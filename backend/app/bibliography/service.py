from fastapi import HTTPException
from sqlalchemy import select
from app.audits.service import requester as requester
from app.bibliography.models import BibliographyJob, BibliographyRun
from app.documents.models import Document, Version
from app.documents.service import MANAGERS, get_document
from app.security import now


def authorized(db, member, run_id, *, lock=False):
    query = select(BibliographyRun).where(
        BibliographyRun.id == run_id, BibliographyRun.institution_id == member.institution_id
    )
    if lock:
        query = query.with_for_update()
    run = db.scalar(query)
    if (
        run is None
        or run.state == "invalidated"
        or run.requester_id != member.id
        and member.role not in MANAGERS | {"auditor"}
    ):
        raise HTTPException(404, "Revisión bibliográfica no disponible")
    version = db.get(Version, run.version_id)
    if version is None:
        raise HTTPException(404, "Versión no disponible")
    get_document(db, member, version.document_id)
    return run


def lock_document(db, run):
    version = db.get(Version, run.version_id)
    db.scalar(select(Document).where(Document.id == version.document_id).with_for_update())


def invalidate(db, version_id):
    for run in db.scalars(
        select(BibliographyRun)
        .where(BibliographyRun.version_id == version_id)
        .order_by(BibliographyRun.id)
        .with_for_update()
    ):
        run.state, run.error_code, run.finished_at = "invalidated", "document_deleted", now()
        run.target_snapshot, run.result, run.summary = {}, {}, {}
        for job in db.scalars(select(BibliographyJob).where(BibliographyJob.run_id == run.id)):
            job.state = "cancelled"
