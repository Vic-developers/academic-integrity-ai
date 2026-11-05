import secrets
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.config import settings
from app.db import context, database
from app.models import Activity, EmailJob, Institution, LoginSession, Membership, ResetToken, User
from app.schemas import InstitutionChoice, Login, ResetConfirm, ResetRequest, UserView
from app.security import DUMMY_HASH, digest, hasher, now, rate_limit, verify

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])
DB = Annotated[Session, Depends(database, scope="function")]


def issue(response: Response, db: Session, user_id: str, institution_id: str | None = None) -> None:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    cfg = settings()
    db.add(
        LoginSession(
            id=digest(token),
            user_id=user_id,
            institution_id=institution_id,
            csrf_hash=digest(csrf),
            expires_at=now() + timedelta(hours=cfg.session_hours),
        )
    )
    opts = dict(secure=cfg.secure_cookies, samesite="lax", path="/", max_age=cfg.session_hours * 3600)
    response.set_cookie("aid_session", token, httponly=True, **opts)
    response.set_cookie("aid_csrf", csrf, httponly=False, **opts)
    response.headers["Cache-Control"] = "no-store"


def current(request: Request, db: DB) -> tuple[User, LoginSession]:
    token = request.cookies.get("aid_session", "")
    session = db.get(LoginSession, digest(token)) if token else None
    if session is None or session.expires_at <= now():
        raise HTTPException(401, "Inicia sesión para continuar")
    user = db.get(User, session.user_id)
    if user is None or not user.active:
        raise HTTPException(401, "Sesión no disponible")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(session.csrf_hash, digest(request.headers.get("x-csrf-token", ""))):
            raise HTTPException(403, "Token CSRF inválido")
    context(db, user_id=user.id, institution_id=session.institution_id or "")
    return user, session


Identity = Annotated[tuple[User, LoginSession], Depends(current)]


def membership(identity: Identity, db: DB) -> Membership:
    user, session = identity
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.institution_id == session.institution_id,
            Membership.active.is_(True),
        )
    )
    if member is None:
        raise HTTPException(403, "Selecciona una institución autorizada")
    return member


Member = Annotated[Membership, Depends(membership)]


def require(member: Membership, *roles: str) -> None:
    if member.role not in roles:
        raise HTTPException(403, "No tienes permiso para esta acción")


@router.post("/login")
def login(body: Login, request: Request, response: Response, db: DB) -> dict:
    rate_limit(request, "login", body.email)
    user = db.scalar(select(User).where(User.email == body.email))
    valid = verify(user.password_hash if user else DUMMY_HASH, body.password)
    if not valid or user is None or not user.active:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    # Rotate the presented session; never reuse a pre-login identifier.
    old = request.cookies.get("aid_session")
    if old:
        db.execute(delete(LoginSession).where(LoginSession.id == digest(old)))
    issue(response, db, user.id)
    return {"message": "Sesión iniciada"}


@router.get("/me")
def me(identity: Identity, db: DB) -> dict:
    user, session = identity
    members = db.execute(
        select(Membership, Institution)
        .join(Institution)
        .where(Membership.user_id == user.id, Membership.active.is_(True))
    ).all()
    return {
        "user": UserView.model_validate(user),
        "institution_id": session.institution_id,
        "memberships": [{"institution_id": i.id, "name": i.name, "role": m.role} for m, i in members],
    }


@router.post("/institution")
def choose(body: InstitutionChoice, identity: Identity, response: Response, db: DB) -> dict:
    user, session = identity
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id, Membership.institution_id == body.institution_id, Membership.active.is_(True)
        )
    )
    if member is None:
        raise HTTPException(403, "Institución no autorizada")
    db.delete(session)
    issue(response, db, user.id, member.institution_id)
    context(db, user_id=user.id, institution_id=member.institution_id)
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="session.institution_selected"))
    return {"message": "Institución seleccionada"}


@router.post("/logout", status_code=204)
def logout(identity: Identity, response: Response, db: DB) -> None:
    db.delete(identity[1])
    response.delete_cookie("aid_session", path="/")
    response.delete_cookie("aid_csrf", path="/")


@router.post("/password-reset/request", status_code=202)
def reset_request(body: ResetRequest, request: Request, db: DB) -> dict:
    email = str(body.email).lower()
    rate_limit(request, "reset", email, maximum=5)
    user = db.scalar(select(User).where(User.email == email, User.active.is_(True)))
    if user:
        # Queue in PostgreSQL; loss of Redis cannot lose this request.
        db.add(EmailJob(user_id=user.id))
    return {"message": "Si la cuenta está activa, recibirás instrucciones por correo"}


@router.post("/password-reset/confirm")
def reset_confirm(body: ResetConfirm, request: Request, db: DB) -> dict:
    rate_limit(request, "reset-confirm")
    # Serialize resets per user, so concurrent tokens cannot both change credentials.
    token = db.get(ResetToken, digest(body.token))
    if token is None:
        raise HTTPException(400, "Enlace inválido o caducado")
    user = db.scalar(select(User).where(User.id == token.user_id).with_for_update())
    token = db.scalar(
        select(ResetToken).where(ResetToken.id == digest(body.token)).execution_options(populate_existing=True)
    )
    if token is None or token.expires_at <= now() or user is None or not user.active:
        raise HTTPException(400, "Enlace inválido o caducado")
    user.password_hash = hasher.hash(body.password)
    db.execute(delete(ResetToken).where(ResetToken.user_id == user.id))
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    # Pending requests from before the reset must not generate new valid links.
    for job in db.scalars(select(EmailJob).where(EmailJob.user_id == user.id, EmailJob.state == "pending")):
        job.state = "cancelled"
    return {"message": "Contraseña actualizada; inicia sesión de nuevo"}
