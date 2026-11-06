from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from app.auth import DB, Member
from app.audits.evidence import snapshot
from app.documents.models import Fragment
from app.documents.service import get_document
from app.experimental_ai.features import FEATURES, VERSION, measure
from app.security import rate_limit

router = APIRouter(prefix="/api/v1/experimental-ai", tags=["Observaciones lingüísticas experimentales"])


@router.get("/capabilities")
def capabilities(member: Member):
    return {
        "observations_available": True,
        "feature_version": VERSION,
        "features": list(FEATURES),
        "authorship_classifier_available": False,
        "approved_model": None,
        "training_via_web_available": False,
        "document_training_allowed": False,
        "external_queries": False,
    }


@router.get("/documents/{document_id}")
def observations(document_id: UUID, request: Request, member: Member, db: DB):
    document, version = get_document(db, member, str(document_id), lock=True)
    if document.state not in {"completed", "partial"}:
        raise HTTPException(409, "Espera a que termine la extracción del documento")
    rate_limit(request, "linguistic-observations", member.id, maximum=300)
    originals = list(
        db.scalars(select(Fragment.original).where(Fragment.version_id == version.id).order_by(Fragment.ordinal))
    )
    if sum(map(len, originals)) + max(0, len(originals) - 1) * 2 > 500000:
        raise HTTPException(413, "El texto supera el presupuesto de observaciones lingüísticas")
    report = measure("\n\n".join(originals))
    if document.state == "partial":
        report["abstention_reasons"].append("partial_document_extraction")
    return {
        "document": snapshot(document, version),
        "observation": report,
        "scope": "extracted_text_joined_with_double_newlines",
        "trained_on_this_document": False,
        "model": None,
    }
