from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from sqlalchemy import select
from app.auth import DB, Member
from app.config import settings
from app.documents.models import Document, DocumentJob, Fragment, Version
from app.documents.service import MANAGERS, get_document, validate_association, visible
from app.documents.storage import object_path, write_original
from app.documents.validation import ERRORS, inspect, safe_name
from app.models import Activity, uid
from app.security import now, rate_limit

router = APIRouter(prefix="/api/v1/documents", tags=["Documentos"])
MIMES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}


@router.get("/limits")
def limits(member: Member) -> dict:
    cfg = settings()
    return {
        "max_file_bytes": cfg.max_file_bytes,
        "max_request_bytes": cfg.max_request_bytes,
        "max_batch_files": cfg.max_batch_files,
        "max_pdf_pages": cfg.max_pdf_pages,
        "ocr_available": False,
        "formats": ["pdf", "docx", "txt"],
    }


def view(document: Document, version: Version) -> dict:
    return {
        "id": document.id,
        "version_id": version.id,
        "name": document.name,
        "state": document.state,
        "owner_id": document.owner_id,
        "assignment_id": document.assignment_id,
        "created_at": document.created_at,
        "format": version.format,
        "size": version.size,
        "sha256": version.sha256,
        "pages": version.page_count,
        "metadata": version.metadata_json,
        "warnings": version.warnings,
        "extractor": version.extractor,
        "error": ERRORS.get(document.error_code, "Error de procesamiento") if document.error_code else None,
        "error_code": document.error_code,
    }


def ingest(db, member, uploaded, assignment, owner) -> dict:
    name = safe_name(uploaded.filename or "")
    format, size, sha = inspect(uploaded.file, name)
    duplicate = db.scalar(
        select(Document.id)
        .join(Version, Version.document_id == Document.id)
        .where(Version.sha256 == sha, Document.deleted_at.is_(None), visible(member))
        .order_by(Document.created_at)
        .limit(1)
    )
    path: Path | None = None
    try:
        with db.begin_nested():
            document = Document(
                id=uid(),
                institution_id=member.institution_id,
                owner_id=owner,
                uploader_id=member.id,
                assignment_id=assignment,
                name=name,
            )
            db.add(document)
            db.flush()
            version = Version(
                id=uid(),
                institution_id=member.institution_id,
                document_id=document.id,
                sha256=sha,
                size=size,
                format=format,
            )
            db.add(version)
            db.flush()
            path = write_original(member.institution_id, version.id, uploaded.file)
            db.info.setdefault("uncommitted_files", []).append(path)
            db.add(DocumentJob(institution_id=member.institution_id, version_id=version.id))
            db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="document.received"))
            db.flush()
            return {**view(document, version), "duplicate_of": duplicate}
    except Exception:
        if path:
            path.unlink(missing_ok=True)
        raise


@router.post(
    "",
    status_code=202,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {"type": "array", "items": {"type": "string", "format": "binary"}},
                            "assignment_id": {"type": "string"},
                            "owner_id": {"type": "string"},
                        },
                        "required": ["files"],
                    }
                }
            },
        }
    },
)
async def upload(request: Request, member: Member, db: DB) -> dict:
    rate_limit(request, "upload", member.id, maximum=50)
    cfg = settings()
    if member.role == "auditor":
        raise HTTPException(403, "El rol auditor es de solo lectura")
    try:
        async with request.form(max_files=cfg.max_batch_files, max_fields=4, max_part_size=4096) as form:
            files = form.getlist("files")
            if not files or len(files) > cfg.max_batch_files or not all(isinstance(f, UploadFile) for f in files):
                raise HTTPException(422, "Selecciona archivos dentro del límite del lote")
            assignment = form.get("assignment_id") or None
            owner = form.get("owner_id") or None
            if (
                assignment is not None
                and not isinstance(assignment, str)
                or owner is not None
                and not isinstance(owner, str)
            ):
                raise HTTPException(422, "Asociación inválida")
            owner = validate_association(db, member, assignment, owner)
            items, errors = [], []
            for index, uploaded in enumerate(files):
                try:
                    items.append(await run_in_threadpool(ingest, db, member, uploaded, assignment, owner))
                except HTTPException as exc:
                    errors.append(
                        {
                            "index": index,
                            "name": (uploaded.filename or "")[:160],
                            "status": exc.status_code,
                            "detail": str(exc.detail),
                        }
                    )
                except OSError:
                    raise HTTPException(503, "No hay almacenamiento privado disponible") from None
            return {"items": items, "errors": errors}
    except HTTPException:
        raise


@router.get("")
def listing(member: Member, db: DB, limit: int = 25, offset: int = 0) -> dict:
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    rows = db.execute(
        select(Document, Version)
        .join(Version, Version.document_id == Document.id)
        .where(Document.deleted_at.is_(None), visible(member))
        .order_by(Document.created_at.desc(), Document.id)
        .offset(offset)
        .limit(limit)
    )
    return {"items": [view(d, v) for d, v in rows]}


@router.get("/{document_id}")
def detail(document_id: UUID, member: Member, db: DB) -> dict:
    document, version = get_document(db, member, str(document_id))
    return {**view(document, version), "can_manage": document.owner_id == member.id or member.role in MANAGERS}


@router.get("/{document_id}/original")
def original(document_id: UUID, member: Member, db: DB) -> FileResponse:
    document, version = get_document(db, member, str(document_id))
    path = object_path(member.institution_id, version.id)
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, "El original no está disponible")
    return FileResponse(
        path, filename=document.name, media_type=MIMES[version.format], content_disposition_type="attachment"
    )


@router.get("/{document_id}/fragments")
def fragments(
    document_id: UUID, member: Member, db: DB, limit: int = 100, offset: int = 0, page: int | None = None
) -> dict:
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "Paginación inválida")
    _, version = get_document(db, member, str(document_id))
    rows = db.scalars(
        select(Fragment)
        .where(
            Fragment.version_id == version.id,
            Fragment.institution_id == member.institution_id,
            Fragment.page == page if page is not None else True,
        )
        .order_by(Fragment.ordinal)
        .offset(offset)
        .limit(limit)
    )
    return {
        "offset_unit": "unicode_code_points",
        "items": [
            {
                "id": f.id,
                "ordinal": f.ordinal,
                "page": f.page,
                "paragraph": f.paragraph,
                "section": f.section,
                "original": f.original,
                "normalized": f.normalized,
                "mapping": f.mapping,
                "locations": f.locations,
                "sentences": f.sentences,
            }
            for f in rows
        ],
    }


@router.post("/{document_id}/cancel")
def cancel(document_id: UUID, member: Member, db: DB) -> dict:
    document, version = get_document(db, member, str(document_id), lock=True)
    if document.owner_id != member.id and member.role not in MANAGERS:
        raise HTTPException(403, "No puedes cancelar este documento")
    if document.state not in {"received", "extracting"}:
        raise HTTPException(409, "El procesamiento ya finalizó")
    document.state = "cancelled"
    for job in db.scalars(
        select(DocumentJob).where(DocumentJob.version_id == version.id, DocumentJob.kind == "extract")
    ):
        job.state = "cancelled"
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="document.cancelled"))
    return {"state": "cancelled"}


@router.delete("/{document_id}", status_code=204)
def remove(document_id: UUID, member: Member, db: DB) -> None:
    document, version = get_document(db, member, str(document_id), lock=True)
    if document.owner_id != member.id and member.role not in MANAGERS:
        raise HTTPException(403, "No puedes eliminar este documento")
    from app.audits.service import invalidate_document

    from sqlalchemy import delete
    from app.semantic.models import SemanticVector

    db.execute(delete(SemanticVector).where(SemanticVector.version_id == version.id))
    invalidate_document(db, version.id)
    from app.bibliography.service import invalidate

    invalidate(db, version.id)
    from app.claims.service import invalidate as invalidate_claims

    invalidate_claims(db, version.id)
    from app.forensics.models import StyleAttestation
    from sqlalchemy import delete

    db.execute(delete(StyleAttestation).where(StyleAttestation.version_id == version.id))
    document.deleted_at = now()
    for job in db.scalars(
        select(DocumentJob).where(DocumentJob.version_id == version.id, DocumentJob.kind == "extract")
    ):
        job.state = "cancelled"
    db.add(DocumentJob(institution_id=member.institution_id, version_id=version.id, kind="purge"))
    db.add(Activity(institution_id=member.institution_id, actor_id=member.id, action="document.deleted"))
