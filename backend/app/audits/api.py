import hashlib
import json
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from app.auth import DB, Member
from app.audits.engine import ENGINE_VERSION, K_GRAM, MIN_WORDS, WINDOW
from app.audits.evidence import snapshot
from app.audits.models import Audit, AuditJob, AuditSource, Finding
from app.audits.service import authorized_audit
from app.config import settings
from app.documents.models import Document, Fragment, Version
from app.documents.normalization import NORMALIZER
from app.documents.service import MANAGERS, get_document, visible
from app.models import Activity
from app.security import now, rate_limit

router = APIRouter(prefix="/api/v1/audits", tags=["Auditorías literales"])


class AuditInput(BaseModel):
    document_id: UUID
    source_document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    request_web: bool = False


def audit_view(audit: Audit, sources: list[AuditSource]) -> dict:
    return {
        "id": audit.id,
        "state": audit.state,
        "target": audit.target_snapshot,
        "sources": [{"id": s.id, "state": s.state, "reason": s.reason, **s.snapshot} for s in sources],
        "coverage": audit.coverage,
        "summary": audit.summary,
        "config": audit.config,
        "engine_version": audit.engine_version,
        "error_code": audit.error_code,
        "created_at": audit.created_at,
        "started_at": audit.started_at,
        "finished_at": audit.finished_at,
    }


@router.get("/capabilities")
def capabilities(member: Member) -> dict:
    cfg = settings()
    return {
        "literal_available": True,
        "engine_version": ENGINE_VERSION,
        "min_words": MIN_WORDS,
        "k_gram": K_GRAM,
        "window": WINDOW,
        "max_sources": min(cfg.max_audit_sources, 20),
        "max_characters": cfg.max_audit_chars,
        "web_available": False,
        "web_reason": "No hay proveedor autorizado y configurado",
        "semantic_available": False,
    }


@router.post("", status_code=202)
def create(
    body: AuditInput,
    request: Request,
    member: Member,
    db: DB,
    idempotency: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> dict:
    rate_limit(request, "audit", member.id, maximum=50)
    ids = sorted(set(str(x) for x in body.source_document_ids))
    if str(body.document_id) in ids or not ids and not body.request_web:
        raise HTTPException(422, "Selecciona fuentes distintas del documento principal")
    if len(ids) > settings().max_audit_sources:
        raise HTTPException(422, "Demasiadas fuentes para una auditoría")
    target, version = get_document(db, member, str(body.document_id))
    rows = [get_document(db, member, id) for id in ids]
    if target.state not in {"completed", "partial"} or any(d.state not in {"completed", "partial"} for d, v in rows):
        raise HTTPException(409, "Espera a que finalice la extracción de todos los documentos")
    # Deterministic row order matches workers and delete; refresh after waiting for concurrent changes.
    list(
        db.scalars(
            select(Document)
            .where(Document.id.in_(ids + [str(body.document_id)]))
            .order_by(Document.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    target, version = get_document(db, member, str(body.document_id))
    rows = [get_document(db, member, id) for id in ids]
    if any(not v.extractor or not v.extractor.endswith("/" + NORMALIZER) for v in [version] + [v for d, v in rows]):
        raise HTTPException(409, "Los documentos no utilizan el normalizador compatible con este motor")
    versions = [version.id] + [v.id for d, v in rows]
    count = db.scalar(
        select(func.coalesce(func.sum(func.length(Fragment.normalized)), 0)).where(Fragment.version_id.in_(versions))
    )
    if count > settings().max_audit_chars:
        raise HTTPException(413, "El conjunto supera el límite de texto de una auditoría CPU")
    target_chars = db.scalar(
        select(func.coalesce(func.sum(func.length(Fragment.normalized)), 0)).where(Fragment.version_id == version.id)
    )
    if not target_chars:
        raise HTTPException(409, "El documento principal no tiene texto extraído")
    request_hash = hashlib.sha256(
        json.dumps(
            {"target": version.id, "sources": sorted(v.id for d, v in rows), "web": body.request_web}, sort_keys=True
        ).encode()
    ).hexdigest()
    if idempotency:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"audit:{member.institution_id}:{member.id}:{idempotency}"},
        )
        old = db.scalar(
            select(Audit).where(
                Audit.institution_id == member.institution_id,
                Audit.requester_id == member.id,
                Audit.idempotency_key == idempotency,
            )
        )
        if old:
            if old.request_hash != request_hash:
                raise HTTPException(409, "La clave ya se utilizó con otra solicitud")
            return audit_view(*authorized_audit(db, member, old.id))
    cfg = settings()
    audit = Audit(
        institution_id=member.institution_id,
        requester_id=member.id,
        target_version_id=version.id,
        idempotency_key=idempotency,
        request_hash=request_hash,
        engine_version=ENGINE_VERSION,
        target_snapshot=snapshot(target, version),
        config={
            "normalizer": NORMALIZER,
            "min_words": MIN_WORDS,
            "k_gram": K_GRAM,
            "window": WINDOW,
            "request_web": body.request_web,
            "max_seeds": cfg.max_literal_seeds,
            "max_checks": cfg.max_literal_checks,
            "max_findings": cfg.max_literal_findings,
        },
    )
    db.add(audit)
    db.flush()
    sources = []
    for document, v in rows:
        source = AuditSource(
            institution_id=member.institution_id, audit_id=audit.id, version_id=v.id, snapshot=snapshot(document, v)
        )
        db.add(source)
        sources.append(source)
    db.add(AuditJob(institution_id=member.institution_id, audit_id=audit.id))
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="audit.requested"))
    db.flush()
    return audit_view(audit, sources)


@router.get("")
def listing(member: Member, db: DB, limit: int = 25, offset: int = 0) -> dict:
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    allowed_versions = (
        select(Version.id)
        .join(Document, Version.document_id == Document.id)
        .where(Document.deleted_at.is_(None), visible(member))
    )
    inaccessible_audits = select(AuditSource.audit_id).where(AuditSource.version_id.not_in(allowed_versions))
    audits = db.scalars(
        select(Audit)
        .where(
            Audit.institution_id == member.institution_id,
            Audit.requester_id == member.id if member.role not in MANAGERS | {"auditor"} else True,
            Audit.state != "invalidated",
            Audit.target_version_id.in_(allowed_versions),
            Audit.id.not_in(inaccessible_audits),
        )
        .order_by(Audit.created_at.desc(), Audit.id)
        .offset(offset)
        .limit(limit)
    )
    items = []
    for audit in audits:
        try:
            items.append(audit_view(*authorized_audit(db, member, audit.id)))
        except HTTPException:
            continue
    return {"items": items}


@router.get("/{audit_id}")
def detail(audit_id: UUID, member: Member, db: DB) -> dict:
    return audit_view(*authorized_audit(db, member, str(audit_id)))


@router.get("/{audit_id}/findings")
def findings(audit_id: UUID, member: Member, db: DB, limit: int = 25, offset: int = 0) -> dict:
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    audit, sources = authorized_audit(db, member, str(audit_id))
    rows = db.scalars(
        select(Finding)
        .where(Finding.audit_id == audit.id)
        .order_by(Finding.target_start, Finding.source_id, Finding.id)
        .offset(offset)
        .limit(limit)
    )
    return {
        "items": [
            {
                "id": f.id,
                "source_id": f.source_id,
                "category": f.category,
                "review_state": f.review_state,
                "word_count": f.word_count,
                "evidence": f.evidence,
            }
            for f in rows
        ]
    }


@router.post("/{audit_id}/cancel")
def cancel(audit_id: UUID, member: Member, db: DB) -> dict:
    audit, sources = authorized_audit(db, member, str(audit_id), lock=True)
    if audit.state not in {"pending", "running"}:
        raise HTTPException(409, "La auditoría ya finalizó")
    audit.state, audit.finished_at = "cancelled", now()
    for job in db.scalars(select(AuditJob).where(AuditJob.audit_id == audit.id)):
        job.state = "cancelled"
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="audit.cancelled"))
    return {"state": "cancelled"}
