"""Real pgvector/SQL tests with labelled synthetic vectors, not semantic inference."""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from app.db import context, engine
from app.documents.models import Fragment
from app.models import Membership
from app.semantic.models import SemanticVector, unit_vector
from app.semantic.store import VectorPassage, retrieve_vectors, store_vectors
from conftest import login
from test_literal import extracted, PHRASE

# Deliberately synthetic identities and unit-basis vectors for numerical/storage tests only.
MODEL = hashlib.sha256(b"technical-fixture-not-a-semantic-model").hexdigest()
OTHER_MODEL = hashlib.sha256(b"different-technical-fixture").hexdigest()
CHUNKER = "technical-fixture-v1"


def vector(x=1.0, y=0.0):
    return [x, y] + [0.0] * 382


def member(db, seed, user="admin", membership="ma", tenant="a"):
    context(db, user_id=seed[user], institution_id=seed[tenant])
    return db.get(Membership, seed[membership])


def index(db, m, document_id, values=None, model=MODEL, chunker=CHUNKER):
    from app.documents.service import get_document

    _, version = get_document(db, m, document_id)
    f = db.scalar(select(Fragment).where(Fragment.version_id == version.id).order_by(Fragment.ordinal))
    return store_vectors(
        db, m, document_id, model, chunker, [VectorPassage(f.id, 0, len(f.original), values or vector())]
    )


@pytest.mark.parametrize(
    "bad",
    [
        [],
        [0.0] * 384,
        [True] + [0.0] * 383,
        [float("nan")] + [0.0] * 383,
        [float("inf")] + [0.0] * 383,
        [10**1000] + [0.0] * 383,
    ],
)
def test_invalid_vectors_never_reach_sql(bad):
    with pytest.raises(ValueError):
        unit_vector(bad)


def test_exact_cosine_query_filters_sources_and_model_before_top_k(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "closest-but-not-selected.txt", PHRASE)
    b = extracted(client, "selected-source.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        index(db, m, a["id"], vector())
        index(db, m, b["id"], vector(0.8, 0.6))
        index(db, m, b["id"], vector(), model=OTHER_MODEL)
        index(db, m, b["id"], vector(), chunker="other-chunker-v1")
        rows = retrieve_vectors(db, m, [b["id"]], MODEL, CHUNKER, vector(), top_k=1)
        assert len(rows) == 1 and rows[0]["document_id"] == b["id"]
        assert rows[0]["cosine"] == pytest.approx(0.8, abs=1e-6)
        assert rows[0]["text"] == PHRASE
        assert rows[0]["interpretation"] == "numeric_vector_candidate_not_a_verified_paraphrase"
        assert rows[0]["input_sha256"] == hashlib.sha256(PHRASE.encode()).hexdigest()
        assert retrieve_vectors(db, m, [b["id"]], OTHER_MODEL, CHUNKER, vector())[0]["cosine"] == pytest.approx(1.0)
        assert retrieve_vectors(db, m, [a["id"]], MODEL, CHUNKER, vector(-1.0, 0.0))[0]["cosine"] == pytest.approx(-1.0)
    # Merely storing vectors must not enable a product engine or create findings.
    assert client.get("/api/v1/audits/capabilities").json()["semantic_available"] is False
    with Session(engine) as db, db.begin():
        member(db, seed)
        assert db.execute(text("SELECT count(*) FROM findings")).scalar_one() == 0


def test_forced_rls_no_context_and_other_tenant_vectors(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "tenant-a.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        index(db, m, a["id"])
    login(client, user="outsider", tenant=seed["b"])
    b = extracted(client, "tenant-b.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed, "outsider", "mb", "b")
        index(db, m, b["id"])
    with Session(engine) as db, db.begin():
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 0
        m = member(db, seed)
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 1
        with pytest.raises(HTTPException) as error:
            retrieve_vectors(db, m, [b["id"]], MODEL, CHUNKER, vector())
        assert error.value.status_code == 404
        with pytest.raises(DBAPIError), db.begin_nested():
            row = db.scalar(select(SemanticVector))
            db.add(
                SemanticVector(
                    institution_id=seed["b"],
                    version_id=row.version_id,
                    fragment_id=row.fragment_id,
                    model_key=OTHER_MODEL,
                    chunker_version=CHUNKER,
                    original_start=0,
                    original_end=row.original_end,
                    input_sha256=row.input_sha256,
                    fragment_sha256=row.fragment_sha256,
                    embedding=vector(),
                )
            )
            db.flush()


def test_document_visibility_and_revocation_same_tenant(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "admin-only.txt", PHRASE)
    b = extracted(client, "teacher-owned.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        index(db, m, a["id"])
        index(db, m, b["id"], vector(0.8, 0.6))
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE documents SET owner_id=:owner WHERE id=:id"), {"owner": seed["mt"], "id": b["id"]})
    with Session(engine) as db, db.begin():
        m = member(db, seed, "teacher", "mt")
        rows = retrieve_vectors(db, m, [b["id"]], MODEL, CHUNKER, vector(), top_k=1)
        assert rows[0]["document_id"] == b["id"]
        with pytest.raises(HTTPException) as error:
            retrieve_vectors(db, m, [a["id"], b["id"]], MODEL, CHUNKER, vector())
        assert error.value.status_code == 404
    with owner.begin() as conn:
        conn.execute(text("UPDATE documents SET owner_id=:owner WHERE id=:id"), {"owner": seed["ms"], "id": b["id"]})
    owner.dispose()
    with Session(engine) as db, db.begin():
        m = member(db, seed, "teacher", "mt")
        with pytest.raises(HTTPException) as error:
            retrieve_vectors(db, m, [b["id"]], MODEL, CHUNKER, vector())
        assert error.value.status_code == 404


def test_cache_idempotence_and_immutable_vector_conflict(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "cache.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        assert index(db, m, a["id"])["inserted"] == 1
        assert index(db, m, a["id"], vector(3.0, 0.0))["inserted"] == 0
        with pytest.raises(HTTPException) as error:
            index(db, m, a["id"], vector(0.0, 1.0))
        assert error.value.status_code == 409
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 1


def test_fragment_version_fk_and_unit_constraint_cannot_be_bypassed(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "a.txt", PHRASE)
    b = extracted(client, "b.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        first = index(db, m, a["id"])
        second = index(db, m, b["id"])
        row = db.scalar(select(SemanticVector).where(SemanticVector.version_id == first["version_id"]))
        with pytest.raises(DBAPIError), db.begin_nested():
            db.add(
                SemanticVector(
                    institution_id=seed["a"],
                    version_id=second["version_id"],
                    fragment_id=row.fragment_id,
                    model_key=OTHER_MODEL,
                    chunker_version=CHUNKER,
                    original_start=0,
                    original_end=row.original_end,
                    input_sha256=row.input_sha256,
                    fragment_sha256=row.fragment_sha256,
                    embedding=vector(),
                )
            )
            db.flush()
        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(
                text("UPDATE semantic_vectors SET embedding=CAST(:value AS vector) WHERE id=:id"),
                {"value": "[" + ",".join(["0"] * 384) + "]", "id": row.id},
            )


def test_delete_purges_vectors_immediately_before_physical_original_purge(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "delete.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        index(db, m, a["id"])
    assert client.delete("/api/v1/documents/" + a["id"]).status_code == 204
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 0
        with pytest.raises(HTTPException):
            retrieve_vectors(db, m, [a["id"]], MODEL, CHUNKER, vector())


def test_fragment_removal_cascades_derived_vectors(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "cascade.txt", PHRASE)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        result = index(db, m, a["id"])
        db.execute(delete(Fragment).where(Fragment.version_id == result["version_id"]))
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 0


def test_original_unicode_span_hash_and_modified_text_rejected(client, seed):
    login(client, tenant=seed["a"])
    value = "🧭 Prefacio. Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho."
    a = extracted(client, "unicode.txt", value)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        index(db, m, a["id"])
        rows = retrieve_vectors(db, m, [a["id"]], MODEL, CHUNKER, vector())
        assert rows[0]["text"] == value and rows[0]["original_end"] == len(value)
        assert rows[0]["input_sha256"] == hashlib.sha256(value.encode()).hexdigest()
        fragment_id = rows[0]["fragment_id"]
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE document_fragments SET original='texto alterado' WHERE id=:id"), {"id": fragment_id})
    owner.dispose()
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        with pytest.raises(HTTPException) as error:
            retrieve_vectors(db, m, [a["id"]], MODEL, CHUNKER, vector())
        assert error.value.status_code == 409


def test_concurrent_indexing_is_idempotent(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "concurrent.txt", PHRASE)

    def write(_):
        with Session(engine) as db, db.begin():
            m = member(db, seed)
            return index(db, m, a["id"])["inserted"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, range(2))) == [0, 1]


def test_version_budget_and_invalid_ranges(client, seed):
    login(client, tenant=seed["a"])
    sentence = "uno dos tres cuatro cinco seis siete ocho"
    value = "\n".join([sentence] * 201)
    a = extracted(client, "budget.txt", value)
    with Session(engine) as db, db.begin():
        m = member(db, seed)
        from app.documents.service import get_document

        _, version = get_document(db, m, a["id"])
        fragment = db.scalar(select(Fragment).where(Fragment.version_id == version.id))
        entries = [
            VectorPassage(fragment.id, i * (len(sentence) + 1), i * (len(sentence) + 1) + len(sentence), vector())
            for i in range(201)
        ]
        assert store_vectors(db, m, a["id"], MODEL, CHUNKER, entries[:200])["inserted"] == 200
        with pytest.raises(HTTPException) as error:
            store_vectors(db, m, a["id"], MODEL, CHUNKER, entries[200:])
        assert error.value.status_code == 409
        assert db.scalar(select(func.count()).select_from(SemanticVector)) == 200
        with pytest.raises(ValueError):
            store_vectors(db, m, a["id"], MODEL, CHUNKER, [VectorPassage(fragment.id, -1, 10, vector())])
        for kwargs in [{"top_k": 0}, {"top_k": 21}, {"top_k": True}]:
            with pytest.raises(ValueError):
                retrieve_vectors(db, m, [a["id"]], MODEL, CHUNKER, vector(), **kwargs)
