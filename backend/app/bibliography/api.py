import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from app.auth import DB, Member, require
from app.audits.evidence import snapshot
from app.bibliography.extraction import VERSION
from app.bibliography.models import BibliographyJob, BibliographyRun
from app.bibliography.service import authorized
from app.config import settings
from app.documents.models import Document, Version
from app.documents.service import MANAGERS, get_document, visible
from app.models import Activity, Institution
from app.security import now, rate_limit

router = APIRouter(prefix="/api/v1/bibliography", tags=["Bibliografía"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    request_external: bool = False
    providers: list[Literal["crossref", "openalex"]] = Field(
        default_factory=lambda: ["crossref", "openalex"], min_length=1, max_length=2
    )


def view(run):
    return {
        "id": run.id,
        "state": run.state,
        "target": run.target_snapshot,
        "config": run.config,
        "summary": run.summary,
        "limitations": run.result.get("limitations", []),
        "heading_found": run.result.get("heading_found"),
        "citations": run.result.get("citations", []),
        "error_code": run.error_code,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


@router.get("/capabilities")
def capabilities(member: Member, db: DB):
    cfg = settings()
    allowed = db.get(Institution, member.institution_id).bibliography_external_allowed
    return {
        "local_available": True,
        "extractor": VERSION,
        "crossref_enabled": cfg.bibliography_external_enabled and allowed,
        "openalex_enabled": cfg.bibliography_external_enabled and allowed and bool(cfg.openalex_api_key),
        "institution_external_allowed": allowed,
        "remote_policy": "Only DOI identifiers, explicit opt-in; never full document text",
        "max_references": 200,
        "max_unique_dois": 10,
        "fulltext_verification_available": False,
    }


class ExternalPolicy(BaseModel):
    allowed: bool


@router.post("/policy")
def policy(body: ExternalPolicy, member: Member, db: DB):
    require(member, "admin", "superadmin")
    institution = db.scalar(select(Institution).where(Institution.id == member.institution_id).with_for_update())
    institution.bibliography_external_allowed = body.allowed
    db.add(
        Activity(
            institution_id=member.institution_id, actor_id=member.id, action="bibliography.external_policy_changed"
        )
    )
    if not body.allowed:
        for run in db.scalars(
            select(BibliographyRun)
            .where(BibliographyRun.state.in_(["pending", "running"]))
            .order_by(BibliographyRun.id)
            .with_for_update()
        ):
            if run.config["request_external"]:
                run.state, run.error_code, run.finished_at = "cancelled", "external_policy_revoked", now()
                run.result, run.summary = {}, {}
                for job in db.scalars(select(BibliographyJob).where(BibliographyJob.run_id == run.id)):
                    job.state = "cancelled"
    return {
        "institution_external_allowed": body.allowed,
        "server_external_enabled": settings().bibliography_external_enabled,
    }


@router.post("", status_code=202)
def create(
    body: Input,
    request: Request,
    member: Member,
    db: DB,
    key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
):
    rate_limit(request, "bibliography", member.id, maximum=30)
    document, version = get_document(db, member, str(body.document_id), lock=True)
    if document.state not in {"completed", "partial"}:
        raise HTTPException(409, "Espera a que termine la extracción")
    config = {"request_external": body.request_external, "providers": sorted(set(body.providers)), "extractor": VERSION}
    fingerprint = hashlib.sha256(json.dumps({"version": version.id, **config}, sort_keys=True).encode()).hexdigest()
    if key:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": member.institution_id + member.id + key},
        )
        old = db.scalar(
            select(BibliographyRun).where(
                BibliographyRun.requester_id == member.id, BibliographyRun.idempotency_key == key
            )
        )
        if old:
            if old.request_hash != fingerprint:
                raise HTTPException(409, "La clave de idempotencia corresponde a otra solicitud")
            return view(authorized(db, member, old.id))
    run = BibliographyRun(
        institution_id=member.institution_id,
        requester_id=member.id,
        version_id=version.id,
        target_snapshot=snapshot(document, version),
        config=config,
        request_hash=fingerprint,
        idempotency_key=key,
    )
    db.add(run)
    db.flush()
    db.add(BibliographyJob(institution_id=member.institution_id, run_id=run.id))
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="bibliography.requested"))
    return view(run)


@router.get("")
def listing(member: Member, db: DB, limit: int = 25, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    allowed = (
        select(Version.id)
        .join(Document, Version.document_id == Document.id)
        .where(Document.deleted_at.is_(None), visible(member))
    )
    rows = db.scalars(
        select(BibliographyRun)
        .where(
            BibliographyRun.state != "invalidated",
            BibliographyRun.version_id.in_(allowed),
            BibliographyRun.requester_id == member.id if member.role not in MANAGERS | {"auditor"} else True,
        )
        .order_by(BibliographyRun.created_at.desc(), BibliographyRun.id)
        .offset(offset)
        .limit(limit)
    )
    return {"items": [view(run) for run in rows]}


@router.get("/{run_id}")
def detail(run_id: UUID, member: Member, db: DB):
    return view(authorized(db, member, str(run_id)))


@router.get("/{run_id}/references")
def references(run_id: UUID, member: Member, db: DB, limit: int = 25, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    run = authorized(db, member, str(run_id))
    return {"items": run.result.get("references", [])[offset : offset + limit]}


@router.get("/{run_id}/references/{ordinal}")
def reference_detail(run_id: UUID, ordinal: int, member: Member, db: DB):
    run = authorized(db, member, str(run_id))
    rows = run.result.get("references", [])
    if not 1 <= ordinal <= len(rows):
        raise HTTPException(404, "Referencia no disponible")
    ref = rows[ordinal - 1]
    snapshots = run.result.get("provider_snapshots", {})
    return {**ref, "provider_responses": [item for item in snapshots.get((ref["fields"]["dois"] or [""])[0], [])]}


@router.post("/{run_id}/cancel")
def cancel(run_id: UUID, member: Member, db: DB):
    run = authorized(db, member, str(run_id), lock=True)
    if run.state not in {"pending", "running"}:
        raise HTTPException(409, "La revisión ya terminó")
    run.state, run.finished_at = "cancelled", now()
    for job in db.scalars(select(BibliographyJob).where(BibliographyJob.run_id == run.id)):
        job.state = "cancelled"
    return {"state": "cancelled"}


@router.get("/{run_id}/export")
def export(run_id: UUID, member: Member, db: DB):
    run = authorized(db, member, str(run_id))
    return Response(
        json.dumps(
            {"schema": "bibliography-evidence-v1", **view(run), "result": run.result}, ensure_ascii=False, default=str
        ),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="bibliografia-{run.id}.json"'},
    )
