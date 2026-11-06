import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from app.auth import DB, Member
from app.audits.evidence import snapshot
from app.claims.engine import VERSION, digest
from app.claims.models import ClaimRun, ClaimSource, Claim, ClaimJob
from app.claims.service import authorized, lock_documents, read_span
from app.documents.models import Document, Version, Fragment
from app.documents.service import MANAGERS, get_document, visible
from app.models import Activity
from app.security import now, rate_limit

router = APIRouter(prefix="/api/v1/claims", tags=["Afirmaciones y revisión humana"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    source_document_ids: list[UUID] = Field(default_factory=list, max_length=20)


class SpanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fragment_id: UUID
    original_start: int = Field(ge=0)
    original_end: int = Field(gt=0)
    fragment_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    span_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class EvidenceInput(SpanInput):
    source_id: UUID


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    state: Literal[
        "unreviewed", "supported", "contradicted", "partially_supported", "not_verifiable", "insufficient_source"
    ]
    reason: str = Field(min_length=10, max_length=2000)
    passages: list[EvidenceInput] = Field(default_factory=list, max_length=5)


def run_view(db, run, sources):
    groups = dict(
        db.execute(
            select(Claim.review_state, func.count()).where(Claim.run_id == run.id).group_by(Claim.review_state)
        ).all()
    )
    return {
        "id": run.id,
        "state": run.state,
        "target": run.target_snapshot,
        "sources": [{"id": s.id, **s.snapshot} for s in sources],
        "config": run.config,
        "summary": {
            **run.summary,
            "human_states": groups,
            "claims_total": sum(groups.values()),
            "human_reviewed": sum(v for k, v in groups.items() if k != "unreviewed"),
        },
        "error_code": run.error_code,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }


def claim_view(claim, *, history=False):
    result = {
        "id": claim.id,
        "ordinal": claim.ordinal,
        "evidence": claim.evidence,
        "review_state": claim.review_state,
        "review_revision": claim.review_revision,
        "last_review": claim.review_log[-1] if claim.review_log else None,
    }
    if history:
        result["review_log"] = claim.review_log
    return result


def find_claim(db, run_id, claim_id, *, lock=False):
    query = select(Claim).where(Claim.run_id == run_id, Claim.id == str(claim_id))
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    claim = db.scalar(query)
    if claim is None:
        raise HTTPException(404, "Afirmación no disponible")
    return claim


@router.get("/capabilities")
def capabilities(member: Member):
    return {
        "local_available": True,
        "engine": VERSION,
        "automatic_entailment_available": False,
        "remote_fetch_available": False,
        "human_assessment_available": True,
        "max_claims": 100,
        "max_sources": 20,
    }


@router.post("", status_code=202)
def create(
    body: Input,
    request: Request,
    member: Member,
    db: DB,
    key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
):
    rate_limit(request, "claims", member.id, maximum=30)
    ids = sorted(set(str(i) for i in body.source_document_ids))
    if str(body.document_id) in ids:
        raise HTTPException(422, "El principal no puede ser una fuente de sí mismo")
    documents = [get_document(db, member, id) for id in sorted(set(ids + [str(body.document_id)]))]
    list(
        db.scalars(
            select(Document)
            .where(Document.id.in_(ids + [str(body.document_id)]))
            .order_by(Document.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    documents = [get_document(db, member, id) for id in sorted(set(ids + [str(body.document_id)]))]
    if any(d.state not in {"completed", "partial"} for d, v in documents):
        raise HTTPException(409, "Espera a que finalice la extracción de todos los documentos")
    versions = {d.id: (d, v) for d, v in documents}
    total = sum(
        len(f)
        for f in db.scalars(select(Fragment.original).where(Fragment.version_id.in_([v.id for d, v in documents])))
    )
    if total > 1_000_000:
        raise HTTPException(413, "El texto combinado supera el presupuesto local")
    document, version = versions[str(body.document_id)]
    config = {
        "engine": VERSION,
        "automatic_entailment": False,
        "external_queries": False,
        "source_version_ids": sorted(versions[id][1].id for id in ids),
    }
    fingerprint = hashlib.sha256(json.dumps({"target": version.id, **config}, sort_keys=True).encode()).hexdigest()
    if key:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": member.institution_id + member.id + key},
        )
        old = db.scalar(select(ClaimRun).where(ClaimRun.requester_id == member.id, ClaimRun.idempotency_key == key))
        if old:
            if old.request_hash != fingerprint:
                raise HTTPException(409, "La clave de idempotencia corresponde a otro alcance")
            run, sources = authorized(db, member, old.id)
            return run_view(db, run, sources)
    run = ClaimRun(
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
    for id in ids:
        d, v = versions[id]
        db.add(
            ClaimSource(institution_id=member.institution_id, run_id=run.id, version_id=v.id, snapshot=snapshot(d, v))
        )
    db.add(ClaimJob(institution_id=member.institution_id, run_id=run.id))
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="claims.requested"))
    db.flush()
    run, sources = authorized(db, member, run.id)
    return run_view(db, run, sources)


@router.get("")
def listing(member: Member, db: DB, limit: int = 25, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    allowed = (
        select(Version.id)
        .join(Document, Version.document_id == Document.id)
        .where(Document.deleted_at.is_(None), visible(member))
    )
    blocked = select(ClaimSource.run_id).where(ClaimSource.version_id.not_in(allowed))
    rows = db.scalars(
        select(ClaimRun)
        .where(
            ClaimRun.state != "invalidated",
            ClaimRun.version_id.in_(allowed),
            ClaimRun.id.not_in(blocked),
            ClaimRun.requester_id == member.id if member.role not in MANAGERS | {"auditor"} else True,
        )
        .order_by(ClaimRun.created_at.desc(), ClaimRun.id)
        .offset(offset)
        .limit(limit)
    )
    return {"items": [run_view(db, *authorized(db, member, r.id)) for r in rows]}


@router.get("/{run_id}")
def detail(run_id: UUID, member: Member, db: DB):
    return run_view(db, *authorized(db, member, str(run_id)))


@router.get("/{run_id}/items")
def items(run_id: UUID, member: Member, db: DB, limit: int = 25, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    run, _ = authorized(db, member, str(run_id))
    rows = db.scalars(
        select(Claim).where(Claim.run_id == run.id).order_by(Claim.ordinal, Claim.id).offset(offset).limit(limit)
    )
    return {"items": [claim_view(c) for c in rows]}


@router.get("/{run_id}/items/{claim_id}")
def item(run_id: UUID, claim_id: UUID, member: Member, db: DB):
    run, _ = authorized(db, member, str(run_id))
    return claim_view(find_claim(db, run.id, claim_id), history=True)


@router.get("/{run_id}/fragments")
def source_fragments(
    run_id: UUID, member: Member, db: DB, source_id: UUID | None = None, limit: int = 25, offset: int = 0
):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    run, sources = authorized(db, member, str(run_id))
    version_id = run.version_id
    if source_id is not None:
        source = next((s for s in sources if s.id == str(source_id)), None)
        if source is None:
            raise HTTPException(404, "Fuente no seleccionada en esta revisión")
        version_id = source.version_id
    rows = db.scalars(
        select(Fragment).where(Fragment.version_id == version_id).order_by(Fragment.ordinal).offset(offset).limit(limit)
    )
    return {
        "offset_unit": "unicode_code_points",
        "items": [
            {
                "id": f.id,
                "original": f.original,
                "page": f.page,
                "paragraph": f.paragraph,
                "fragment_sha256": digest(f.original),
            }
            for f in rows
        ],
    }


@router.post("/{run_id}/items", status_code=201)
def manual(run_id: UUID, body: SpanInput, member: Member, db: DB):
    run, _ = authorized(db, member, str(run_id))
    lock_documents(db, run)
    run, _ = authorized(db, member, run.id, lock=True)
    if member.role not in MANAGERS | {"teacher", "auditor"}:
        raise HTTPException(403, "La selección manual requiere un evaluador")
    if run.state not in {"completed", "partial"}:
        raise HTTPException(409, "Espera a que termine el trabajo")
    if db.scalar(select(func.count()).select_from(Claim).where(Claim.run_id == run.id)) >= 100:
        raise HTTPException(409, "Límite de afirmaciones alcanzado")
    span = read_span(
        db,
        run.version_id,
        str(body.fragment_id),
        body.original_start,
        body.original_end,
        body.fragment_sha256,
        body.span_sha256,
    )
    old = db.scalar(
        select(Claim).where(
            Claim.run_id == run.id,
            Claim.fragment_id == span["fragment_id"],
            Claim.original_start == body.original_start,
            Claim.original_end == body.original_end,
        )
    )
    if old:
        return claim_view(old, history=True)
    ordinal = (db.scalar(select(func.max(Claim.ordinal)).where(Claim.run_id == run.id)) or 0) + 1
    claim = Claim(
        institution_id=member.institution_id,
        run_id=run.id,
        version_id=run.version_id,
        fragment_id=span["fragment_id"],
        original_start=body.original_start,
        original_end=body.original_end,
        ordinal=ordinal,
        evidence={
            "origin": "manual_selection",
            "span": span,
            "candidates": [],
            "citation_context": [],
            "evidence_state": "manual_selection",
            "automatic_verdict": "not_assessed",
        },
    )
    db.add(claim)
    db.flush()
    return claim_view(claim, history=True)


@router.post("/{run_id}/items/{claim_id}/review")
def review(run_id: UUID, claim_id: UUID, body: ReviewInput, member: Member, db: DB):
    run, _ = authorized(db, member, str(run_id))
    if member.role not in MANAGERS | {"teacher", "auditor"}:
        raise HTTPException(403, "La evaluación requiere un evaluador autorizado")
    if len(body.reason.strip()) < 10:
        raise HTTPException(422, "Indica un motivo concreto")
    if body.state in {"supported", "contradicted", "partially_supported"} and not body.passages:
        raise HTTPException(422, "Esta clasificación requiere al menos un pasaje de una fuente seleccionada")
    lock_documents(db, run)
    run, sources = authorized(db, member, run.id, lock=True)
    if run.state not in {"completed", "partial"}:
        raise HTTPException(409, "El trabajo no admite revisión en este estado")
    claim = find_claim(db, run.id, claim_id, lock=True)
    if claim.review_revision != body.expected_revision:
        raise HTTPException(409, "Otra revisión modificó la afirmación; actualiza antes de guardar")
    target = claim.evidence["span"]
    read_span(
        db,
        run.version_id,
        claim.fragment_id,
        claim.original_start,
        claim.original_end,
        target["fragment_sha256"],
        target["span_sha256"],
    )
    evidence = []
    for selected in body.passages:
        source = next((s for s in sources if s.id == str(selected.source_id)), None)
        if source is None:
            raise HTTPException(404, "Fuente no seleccionada en esta revisión")
        span = read_span(
            db,
            source.version_id,
            str(selected.fragment_id),
            selected.original_start,
            selected.original_end,
            selected.fragment_sha256,
            selected.span_sha256,
        )
        evidence.append({"source_id": source.id, "source_snapshot": source.snapshot, "span": span})
    event = {
        "revision": claim.review_revision + 1,
        "state": body.state,
        "reason": body.reason.strip(),
        "passages": evidence,
        "actor_id": member.id,
        "at": now().isoformat(),
        "basis": "human_review_of_selected_document_passages",
    }
    log = [*claim.review_log, event]
    if len(log) > 50 or len(json.dumps(log, ensure_ascii=False).encode()) > 256 * 1024:
        raise HTTPException(409, "Se alcanzó el presupuesto de historial de esta afirmación")
    claim.review_state, claim.review_revision, claim.review_log = body.state, event["revision"], log
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="claim.reviewed"))
    return claim_view(claim, history=True)


@router.post("/{run_id}/cancel")
def cancel(run_id: UUID, member: Member, db: DB):
    run, _ = authorized(db, member, str(run_id), lock=True)
    if run.state not in {"pending", "running"}:
        raise HTTPException(409, "El trabajo ya terminó")
    run.state, run.finished_at = "cancelled", now()
    for job in db.scalars(select(ClaimJob).where(ClaimJob.run_id == run.id)):
        job.state = "cancelled"
    return {"state": "cancelled"}


@router.get("/{run_id}/export")
def export(run_id: UUID, member: Member, db: DB):
    run, sources = authorized(db, member, str(run_id))
    claims = list(db.scalars(select(Claim).where(Claim.run_id == run.id).order_by(Claim.ordinal)))
    payload = {
        "schema": "claim-human-evidence-v1",
        "run": run_view(db, run, sources),
        "claims": [claim_view(c, history=True) for c in claims],
        "warning": "Human assessment, not automated truth verification or plagiarism proof",
    }
    return Response(
        json.dumps(payload, ensure_ascii=False, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="afirmaciones-{run.id}.json"'},
    )
