from fastapi import HTTPException
from sqlalchemy import delete, select, or_
from app.audits.service import requester as requester
from app.claims.models import ClaimRun, ClaimSource, Claim, ClaimJob
from app.documents.models import Document, Version, Fragment
from app.documents.service import MANAGERS, get_document
from app.claims.engine import evidence
from app.security import now


def authorized(db, member, run_id, *, lock=False):
    query = select(ClaimRun).where(ClaimRun.id == run_id, ClaimRun.institution_id == member.institution_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    run = db.scalar(query)
    if (
        run is None
        or run.state == "invalidated"
        or run.requester_id != member.id
        and member.role not in MANAGERS | {"auditor"}
    ):
        raise HTTPException(404, "Revisión de afirmaciones no disponible")
    sources = list(db.scalars(select(ClaimSource).where(ClaimSource.run_id == run.id).order_by(ClaimSource.id)))
    for version_id in [run.version_id] + [s.version_id for s in sources]:
        version = db.get(Version, version_id)
        if version is None:
            raise HTTPException(404, "Versión no disponible")
        get_document(db, member, version.document_id)
    return run, sources


def lock_documents(db, run):
    version_ids = [run.version_id] + list(
        db.scalars(select(ClaimSource.version_id).where(ClaimSource.run_id == run.id))
    )
    ids = select(Version.document_id).where(Version.id.in_(version_ids))
    list(db.scalars(select(Document).where(Document.id.in_(ids)).order_by(Document.id).with_for_update()))


def read_span(db, version_id, fragment_id, start, end, expected_fragment_hash, expected_span_hash=None):
    fragment = db.scalar(select(Fragment).where(Fragment.id == fragment_id, Fragment.version_id == version_id))
    if fragment is None:
        raise HTTPException(404, "Pasaje no disponible en esta versión")
    if not 0 <= start < end <= len(fragment.original) or end - start > 2000:
        raise HTTPException(422, "Selecciona un pasaje de hasta 2000 puntos de código")
    item = evidence(
        {"id": fragment.id, "original": fragment.original, "page": fragment.page, "paragraph": fragment.paragraph},
        start,
        end,
    )
    if (
        item["fragment_sha256"] != expected_fragment_hash
        or expected_span_hash is not None
        and item["span_sha256"] != expected_span_hash
    ):
        raise HTTPException(409, "El pasaje cambió; vuelve a consultar la versión original")
    if not item["text"].strip():
        raise HTTPException(422, "El pasaje no puede estar vacío")
    return item


def invalidate(db, version_id):
    ids = select(ClaimRun.id).where(
        or_(
            ClaimRun.version_id == version_id,
            ClaimRun.id.in_(select(ClaimSource.run_id).where(ClaimSource.version_id == version_id)),
        )
    )
    for run in db.scalars(select(ClaimRun).where(ClaimRun.id.in_(ids)).order_by(ClaimRun.id).with_for_update()):
        run.state, run.error_code, run.finished_at = "invalidated", "document_deleted", now()
        run.target_snapshot, run.summary = {}, {}
        db.execute(delete(Claim).where(Claim.run_id == run.id))
        for source in db.scalars(select(ClaimSource).where(ClaimSource.run_id == run.id)):
            source.snapshot = {}
        for job in db.scalars(select(ClaimJob).where(ClaimJob.run_id == run.id)):
            job.state = "cancelled"
