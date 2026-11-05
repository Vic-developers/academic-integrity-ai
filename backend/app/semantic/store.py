"""Internal pgvector primitives, not a public semantic engine or a model approval bypass.

Only a future verified inference worker may supply actual embeddings. No application
route calls this module to index documents or produce findings while inference is off.
"""

import hashlib
import math
import re
from dataclasses import dataclass
from fastapi import HTTPException
from sqlalchemy import Float, select
from sqlalchemy.orm import Session
from app.documents.models import Document, Fragment, Version
from app.documents.service import get_document, visible
from app.models import Membership
from app.semantic.models import SemanticVector, Vector384, unit_vector
from sqlalchemy import bindparam


@dataclass(frozen=True)
class VectorPassage:
    fragment_id: str
    start: int
    end: int
    vector: list[float]


def identity(model_key: str, chunker_version: str):
    if (
        not isinstance(model_key, str)
        or not isinstance(chunker_version, str)
        or not re.fullmatch(r"[0-9a-f]{64}", model_key)
        or not re.fullmatch(r"[a-z0-9._-]{1,64}", chunker_version)
    ):
        raise ValueError("Invalid model or chunker identity")


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def store_vectors(
    db: Session,
    member: Membership,
    document_id: str,
    model_key: str,
    chunker_version: str,
    passages: list[VectorPassage],
) -> dict:
    identity(model_key, chunker_version)
    if not 1 <= len(passages) <= 200:
        raise ValueError("Index batches must contain 1–200 passages")
    document, version = get_document(db, member, document_id, lock=True)
    if document.state not in {"completed", "partial"}:
        raise HTTPException(409, "La extracción aún no está disponible")
    fragments = {f.id: f for f in db.scalars(select(Fragment).where(Fragment.version_id == version.id))}
    existing = list(
        db.scalars(
            select(SemanticVector).where(
                SemanticVector.version_id == version.id,
                SemanticVector.model_key == model_key,
                SemanticVector.chunker_version == chunker_version,
            )
        )
    )
    indexed = {(v.fragment_id, v.original_start, v.original_end): v for v in existing}
    pending = {}
    for passage in passages:
        fragment = fragments.get(passage.fragment_id)
        if fragment is None:
            raise HTTPException(404, "Fragmento no disponible en esta versión")
        a, b = passage.start, passage.end
        if (
            isinstance(a, bool)
            or isinstance(b, bool)
            or not isinstance(a, int)
            or not isinstance(b, int)
            or not 0 <= a < b <= len(fragment.original)
            or b - a > 4096
        ):
            raise ValueError("Invalid original codepoint range")
        original = fragment.original[a:b]
        if len(re.findall(r"\w+", original)) < 8:
            raise ValueError("Passage is below the minimum of eight words")
        vector = unit_vector(passage.vector)
        key = (fragment.id, a, b)
        prior = indexed.get(key) or pending.get(key)
        if prior is not None:
            if (
                prior.input_sha256 != sha(original)
                or prior.fragment_sha256 != sha(fragment.original)
                or not all(
                    math.isclose(x, y, abs_tol=1e-7, rel_tol=1e-6) for x, y in zip(prior.embedding, vector, strict=True)
                )
            ):
                raise HTTPException(
                    409, "El vector ya existe con otro contenido; no se sobrescribe una revisión inmutable"
                )
            continue
        pending[key] = SemanticVector(
            institution_id=member.institution_id,
            version_id=version.id,
            fragment_id=fragment.id,
            model_key=model_key,
            chunker_version=chunker_version,
            original_start=a,
            original_end=b,
            input_sha256=sha(original),
            fragment_sha256=sha(fragment.original),
            embedding=vector,
        )
    if len(indexed) + len(pending) > 200:
        raise HTTPException(409, "Se alcanzó el presupuesto de pasajes de esta versión y modelo")
    # All range/identity checks precede writes; the document lock serializes competing indexers and delete.
    db.add_all(pending.values())
    db.flush()
    return {
        "inserted": len(pending),
        "existing": len(indexed),
        "version_id": version.id,
        "model_key": model_key,
        "chunker_version": chunker_version,
    }


def retrieve_vectors(
    db: Session,
    member: Membership,
    document_ids: list[str],
    model_key: str,
    chunker_version: str,
    query_vector: list[float],
    *,
    top_k=5,
) -> list[dict]:
    identity(model_key, chunker_version)
    if (
        not 1 <= len(document_ids) <= 20
        or isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or not 1 <= top_k <= 20
    ):
        raise ValueError("Invalid source or top-k budget")
    query = unit_vector(query_vector)
    versions = [get_document(db, member, id)[1].id for id in sorted(set(document_ids))]
    distance = SemanticVector.embedding.op("<=>", return_type=Float)(bindparam("query_vector", type_=Vector384()))
    # Exact search: tenant, selected versions, model identity and live permissions are filtered BEFORE top-k.
    rows = db.execute(
        select(SemanticVector, Fragment, Version, distance.label("distance"))
        .join(Fragment, SemanticVector.fragment_id == Fragment.id)
        .join(Version, SemanticVector.version_id == Version.id)
        .join(Document, Version.document_id == Document.id)
        .where(
            SemanticVector.institution_id == member.institution_id,
            SemanticVector.version_id.in_(versions),
            SemanticVector.model_key == model_key,
            SemanticVector.chunker_version == chunker_version,
            Document.deleted_at.is_(None),
            visible(member),
        )
        .order_by(distance, SemanticVector.id)
        .limit(top_k),
        {"query_vector": query},
    )
    result = []
    for vector, fragment, version, value in rows:
        original = fragment.original[vector.original_start : vector.original_end]
        if sha(original) != vector.input_sha256 or sha(fragment.original) != vector.fragment_sha256:
            raise HTTPException(409, "La caché vectorial no coincide con su fragmento original")
        result.append(
            {
                "id": vector.id,
                "document_id": version.document_id,
                "version_id": version.id,
                "fragment_id": fragment.id,
                "page": fragment.page,
                "paragraph": fragment.paragraph,
                "original_start": vector.original_start,
                "original_end": vector.original_end,
                "text": original,
                "input_sha256": vector.input_sha256,
                "document_sha256": version.sha256,
                "model_key": model_key,
                "chunker_version": chunker_version,
                "cosine": max(-1.0, min(1.0, 1.0 - float(value))),
                "interpretation": "numeric_vector_candidate_not_a_verified_paraphrase",
            }
        )
    return result
