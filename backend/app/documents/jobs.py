import uuid
import hashlib
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from app.db import context, engine
from app.documents.models import Document, DocumentJob, Fragment, Version
from app.documents.runner import run_extractor
from app.documents.storage import object_path
from app.documents.validation import DocumentError


def process_next() -> bool:
    token = str(uuid.uuid4())
    with Session(engine) as db, db.begin():
        db.execute(text("SELECT public.fail_exhausted_document_jobs()"))
        claimed = db.execute(text("SELECT * FROM public.claim_document_job(:token)"), {"token": token}).first()
    if claimed is None:
        return False
    job_id, tenant = claimed
    error, result = None, None
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        job = db.get(DocumentJob, job_id)
        version = db.get(Version, job.version_id)
        document = db.scalar(select(Document).where(Document.id == version.document_id).with_for_update())
        job = db.scalar(
            select(DocumentJob)
            .where(DocumentJob.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job is None or job.state != "running" or job.lease_token != token:
            return True
        if job.kind == "extract" and (document.deleted_at or document.state == "cancelled"):
            job.state = "cancelled"
            return True
        if job.kind == "purge":
            # Delete immediately revokes access; physical purge is durable and idempotent.
            try:
                object_path(tenant, version.id).unlink(missing_ok=True)
                db.execute(delete(Fragment).where(Fragment.version_id == version.id))
                version.metadata_json, version.warnings = {}, ["original_purged"]
                job.state = "done"
            except OSError:
                job.state = "pending" if job.attempts < 3 else "failed"
            return True
        document.state = "extracting"
        version_id, format = version.id, version.format
        expected_hash, expected_size = version.sha256, version.size
        document_id = document.id
    try:
        path = object_path(tenant, version_id)
        if not path.is_file() or path.is_symlink():
            raise DocumentError("storage_unavailable")
        with path.open("rb") as original:
            stored_hash = hashlib.file_digest(original, "sha256").hexdigest()
        if stored_hash != expected_hash or path.stat().st_size != expected_size:
            raise DocumentError("integrity_error")
        result = run_extractor(path, format)
    except DocumentError as exc:
        error = exc.code
    except Exception:
        error = "extraction_failed"
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        # Same document->job lock order as cancel/delete. An expired claim cannot overwrite a new run.
        document = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
        job = db.scalar(select(DocumentJob).where(DocumentJob.id == job_id).with_for_update())
        if job is None or job.lease_token != token or job.state != "running":
            return True
        if document.deleted_at or document.state == "cancelled":
            job.state = "cancelled"
            return True
        version = db.get(Version, version_id)
        if error:
            document.state, document.error_code, job.state = "failed", error, "failed"
        else:
            db.execute(delete(Fragment).where(Fragment.version_id == version_id))
            for ordinal, f in enumerate(result["fragments"], 1):
                db.add(Fragment(institution_id=tenant, version_id=version_id, ordinal=ordinal, **f))
            version.metadata_json, version.warnings = result["metadata"], result["warnings"]
            version.page_count, version.extractor = result["pages"], result["extractor"]
            document.state, document.error_code = "partial" if result["partial"] else "completed", None
            job.state = "done"
    return True
