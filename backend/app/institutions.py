from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from app.auth import DB, Member, require
from app.models import Activity, Membership, User
from app.schemas import UserCreate, UserView
from app.security import hasher

router = APIRouter(prefix="/api/v1", tags=["Instituciones"])


@router.get("/users")
def users(member: Member, db: DB, limit: int = 25, offset: int = 0) -> dict:
    require(member, "superadmin", "admin", "coordinator")
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    rows = db.execute(
        select(User, Membership)
        .join(Membership)
        .where(Membership.institution_id == member.institution_id)
        .order_by(User.email)
        .offset(offset)
        .limit(limit)
    ).all()
    return {"items": [{**UserView.model_validate(u).model_dump(), "role": m.role} for u, m in rows]}


@router.post("/users", status_code=201)
def create_user(body: UserCreate, member: Member, db: DB) -> dict:
    require(member, "superadmin", "admin")
    if body.role == "superadmin":
        raise HTTPException(403, "Superadministración se provisiona por CLI")
    email = str(body.email).lower()
    # No attaching existing identities by guessing an email; requires future invitation workflow.
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "No se pudo crear el usuario; consulta al administrador")
    user = User(email=email, name=body.name, password_hash=hasher.hash(body.password))
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, institution_id=member.institution_id, role=body.role))
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="user.created"))
    return UserView.model_validate(user).model_dump()


@router.get("/activity")
def activity(member: Member, db: DB, limit: int = 25) -> dict:
    require(member, "superadmin", "admin", "coordinator", "auditor")
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Límite inválido")
    rows = db.scalars(
        select(Activity)
        .where(Activity.institution_id == member.institution_id)
        .order_by(Activity.created_at.desc(), Activity.id)
        .limit(limit)
    )
    return {"items": [{"id": a.id, "action": a.action, "created_at": a.created_at} for a in rows]}


@router.get("/statistics")
def statistics(member: Member, db: DB) -> dict:
    count = db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.institution_id == member.institution_id, Membership.active.is_(True))
    )
    return {
        "active_members": count,
        "phase": 2,
        "capabilities": {"documents": True, "audits": False, "semantic": False, "ai": False},
    }
