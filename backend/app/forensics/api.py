import json
from datetime import date
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.auth import DB, Member
from app.audits.evidence import snapshot
from app.audits.jobs import fragments
from app.documents.models import Document, Fragment
from app.documents.service import MANAGERS, get_document
from app.forensics.engine import analyze, style_comparison
from app.forensics.models import StyleAttestation
from app.models import Activity, Membership, User
from app.security import now, rate_limit

router = APIRouter(prefix="/api/v1/forensics", tags=["Forense y comparación descriptiva de estilo"])
EVALUATORS = MANAGERS | {"teacher", "auditor"}


class AttestationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    active: bool = True
    verified_writing_sample: bool = False
    authorization_reference: str = Field(min_length=10, max_length=1000)
    provenance_reference: str = Field(min_length=10, max_length=1000)
    language: str = Field(min_length=2, max_length=30)
    domain: str = Field(min_length=3, max_length=100)
    genre: str = Field(min_length=3, max_length=100)
    sample_date: date
    reason: str = Field(min_length=10, max_length=1000)


class ComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    source_document_ids: list[UUID] = Field(min_length=2, max_length=5)
    expected_revisions: dict[str, int]


def evaluator(member):
    if member.role not in EVALUATORS:
        raise HTTPException(403, "Se requiere un evaluador autorizado")


def attestation_view(item):
    if item is None:
        return {"revision": 0, "active": False, "details": {}, "history": []}
    return {
        "revision": item.revision,
        "active": item.active,
        "student_id": item.student_id,
        "details": item.details,
        "history": item.history,
    }


def ready(db, member, id, lock=False):
    document, version = get_document(db, member, str(id), lock=lock)
    if document.state not in {"completed", "partial"}:
        raise HTTPException(409, "Espera a que termine la extracción")
    return document, version


@router.get("/documents/{document_id}")
def report(document_id: UUID, request: Request, member: Member, db: DB):
    document, version = ready(db, member, document_id, lock=True)
    rate_limit(request, "forensic-read", member.id, maximum=300)
    try:
        result = analyze(fragments(db, version.id), version.metadata_json, version.extractor)
    except ValueError:
        raise HTTPException(413, "El texto supera el presupuesto forense") from None
    return {
        "document": snapshot(document, version),
        "observation": result,
        "extraction_partial": document.state == "partial",
        "claim_of_misconduct": False,
    }


@router.get("/documents/{document_id}/attestation")
def attestation(document_id: UUID, member: Member, db: DB):
    document, version = ready(db, member, document_id)
    item = db.scalar(select(StyleAttestation).where(StyleAttestation.version_id == version.id))
    return attestation_view(item)


@router.post("/documents/{document_id}/attestation")
def attest(document_id: UUID, body: AttestationInput, member: Member, db: DB):
    evaluator(member)
    document, version = ready(db, member, document_id, lock=True)
    item = db.scalar(select(StyleAttestation).where(StyleAttestation.version_id == version.id).with_for_update())
    revision = item.revision if item else 0
    if revision != body.expected_revision:
        raise HTTPException(409, "La autorización cambió; actualiza antes de guardar")
    student = db.scalar(
        select(Membership)
        .join(User, Membership.user_id == User.id)
        .where(
            User.active.is_(True),
            Membership.id == document.owner_id,
            Membership.role == "student",
            Membership.active.is_(True),
        )
    )
    if body.active and student is None:
        raise HTTPException(422, "La comparación exige documentos del mismo estudiante activo")
    details = body.model_dump(mode="json", exclude={"expected_revision", "active"})
    for key in ["authorization_reference", "provenance_reference", "reason", "language", "domain", "genre"]:
        details[key] = details[key].strip()
        if len(details[key]) < (2 if key == "language" else 3 if key in {"domain", "genre"} else 10):
            raise HTTPException(422, "Completa la autorización y la procedencia")
    if body.sample_date > date.today():
        raise HTTPException(422, "La fecha de muestra no puede estar en el futuro")
    event = {
        "revision": revision + 1,
        "active": body.active,
        "details": details,
        "actor_id": member.id,
        "at": now().isoformat(),
    }
    history = [*(item.history if item else []), event]
    if len(history) > 20 or len(json.dumps(history).encode()) > 64 * 1024:
        raise HTTPException(409, "Límite de historial de autorización alcanzado")
    if item is None:
        if student is None:
            raise HTTPException(422, "No hay una autorización previa que revocar")
        item = StyleAttestation(institution_id=member.institution_id, version_id=version.id, student_id=student.id)
        db.add(item)
    if body.active:
        item.student_id = student.id
    item.active, item.revision, item.details, item.history = body.active, revision + 1, details, history
    db.add(
        Activity(
            institution_id=member.institution_id,
            actor_id=member.id,
            action="style.attested" if body.active else "style.authorization_revoked",
        )
    )
    db.flush()
    return attestation_view(item)


@router.post("/style/compare")
def compare(body: ComparisonInput, request: Request, member: Member, db: DB):
    evaluator(member)
    ids = [str(body.document_id), *map(str, body.source_document_ids)]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "Selecciona documentos distintos")
    rate_limit(request, "style-comparison", member.id, maximum=120)
    docs = {id: ready(db, member, id) for id in sorted(ids)}
    list(
        db.scalars(
            select(Document)
            .where(Document.id.in_(ids))
            .order_by(Document.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    docs = {id: ready(db, member, id) for id in sorted(ids)}
    records = {}
    for id in sorted(ids):
        d, v = docs[id]
        item = db.scalar(select(StyleAttestation).where(StyleAttestation.version_id == v.id).with_for_update())
        if item is None or not item.active:
            raise HTTPException(409, "Falta autorización activa para una de las muestras")
        if body.expected_revisions.get(id) != item.revision:
            raise HTTPException(409, "La autorización cambió; vuelve a consultar las muestras")
        student = db.scalar(
            select(Membership)
            .join(User, Membership.user_id == User.id)
            .where(
                User.active.is_(True),
                Membership.id == d.owner_id,
                Membership.role == "student",
                Membership.active.is_(True),
            )
        )
        if student is None or student.id != item.student_id:
            raise HTTPException(409, "La vinculación del estudiante ya no es válida")
        if d.state == "partial":
            raise HTTPException(409, "La comparación requiere extracciones completas")
        records[id] = item
    target = records[str(body.document_id)]
    for id in ids[1:]:
        item = records[id]
        if item.student_id != target.student_id:
            raise HTTPException(422, "Las muestras deben pertenecer al mismo estudiante")
        if not item.details["verified_writing_sample"]:
            raise HTTPException(422, "Las muestras anteriores requieren verificación humana explícita")
        if any(
            item.details[key].casefold() != target.details[key].casefold() for key in ["language", "domain", "genre"]
        ):
            raise HTTPException(422, "Idioma, dominio y género deben ser comparables")
        if item.details["sample_date"] >= target.details["sample_date"]:
            raise HTTPException(422, "Las muestras verificadas deben ser anteriores al trabajo")
    versions = [v.id for d, v in docs.values()]
    total = db.scalars(select(Fragment.original).where(Fragment.version_id.in_(versions)))
    if sum(map(len, total)) > 499980:
        raise HTTPException(413, "Se excedió el presupuesto combinado de estilo")
    texts = {
        id: "\n\n".join(
            db.scalars(select(Fragment.original).where(Fragment.version_id == v.id).order_by(Fragment.ordinal))
        )
        for id, (d, v) in docs.items()
    }
    try:
        result = style_comparison(texts[ids[0]], [texts[id] for id in ids[1:]])
    except ValueError as exc:
        raise HTTPException(
            422,
            {
                "style_sample_below_100_tokens": "Cada muestra necesita al menos cien tokens",
                "duplicate_style_text": "Las muestras contienen texto duplicado",
                "style_text_budget": "Presupuesto de estilo excedido",
            }.get(str(exc), "Comparación no disponible"),
        ) from None
    return {
        "target": snapshot(*docs[ids[0]]),
        "sources": [snapshot(*docs[id]) for id in ids[1:]],
        "attestations": {id: attestation_view(records[id]) for id in ids},
        "comparison": result,
        "claim_of_misconduct": False,
        "generated_at": now().isoformat(),
    }
