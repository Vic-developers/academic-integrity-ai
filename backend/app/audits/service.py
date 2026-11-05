from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session
from app.audits.models import Audit, AuditJob, AuditSource, Finding
from app.documents.models import Document, Version
from app.documents.service import MANAGERS, get_document
from app.models import Membership, User
from app.security import now


def authorized_audit(
    db: Session, member: Membership, audit_id: str, *, lock: bool = False
) -> tuple[Audit, list[AuditSource]]:
    query = select(Audit).where(Audit.id == audit_id, Audit.institution_id == member.institution_id)
    if lock:
        query = query.with_for_update()
    audit = db.scalar(query)
    if audit is None or audit.requester_id != member.id and member.role not in MANAGERS | {"auditor"}:
        raise HTTPException(404, "Auditoría no disponible")
    # Revalidate all source permissions before returning even a filename or a count.
    versions = [audit.target_version_id]
    sources = list(
        db.scalars(
            select(AuditSource)
            .where(AuditSource.audit_id == audit.id, AuditSource.institution_id == member.institution_id)
            .order_by(AuditSource.id)
        )
    )
    versions.extend(s.version_id for s in sources)
    for version_id in versions:
        version = db.get(Version, version_id)
        if version is None:
            raise HTTPException(404, "Auditoría no disponible")
        try:
            get_document(db, member, version.document_id)
        except HTTPException:
            raise HTTPException(404, "Auditoría no disponible") from None
    return audit, sources


def requester(db: Session, audit: Audit) -> Membership:
    member = db.scalar(
        select(Membership)
        .join(User, Membership.user_id == User.id)
        .where(
            Membership.id == audit.requester_id,
            Membership.institution_id == audit.institution_id,
            Membership.active.is_(True),
            User.active.is_(True),
        )
    )
    if member is None:
        raise HTTPException(403, "Solicitante sin autorización vigente")
    return member


def lock_documents(db: Session, audit_id: str) -> None:
    audit = db.get(Audit, audit_id)
    version_ids = [audit.target_version_id] + list(
        db.scalars(select(AuditSource.version_id).where(AuditSource.audit_id == audit_id))
    )
    ids = list(db.scalars(select(Version.document_id).where(Version.id.in_(version_ids))))
    list(db.scalars(select(Document).where(Document.id.in_(ids)).order_by(Document.id).with_for_update()))


def invalidate_document(db: Session, version_id: str) -> None:
    ids = list(
        db.scalars(
            select(Audit.id)
            .where(
                or_(
                    Audit.target_version_id == version_id,
                    Audit.id.in_(select(AuditSource.audit_id).where(AuditSource.version_id == version_id)),
                )
            )
            .order_by(Audit.id)
        )
    )
    for audit in db.scalars(select(Audit).where(Audit.id.in_(ids)).order_by(Audit.id).with_for_update()):
        audit.state, audit.error_code, audit.finished_at = "invalidated", "document_deleted", now()
        audit.summary, audit.coverage = {}, {}
        audit.target_snapshot = {}  # Remove derivative filenames and cached metadata immediately.
        for source in db.scalars(select(AuditSource).where(AuditSource.audit_id == audit.id)):
            source.snapshot = {}
        db.execute(delete(Finding).where(Finding.audit_id == audit.id))
        for job in db.scalars(select(AuditJob).where(AuditJob.audit_id == audit.id)):
            job.state = "cancelled"
