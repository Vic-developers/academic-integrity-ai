"""Synthetic claims test provenance and human decisions, never model accuracy."""

import uuid
import pytest
from app.claims.engine import analyze, digest
from app.claims import jobs
from conftest import login
from test_literal import extracted, parts

FACT = "🧭 El estudio sintético indica que la lectura aumenta el rendimiento en 12.5 puntos."
NEGATION = "El estudio sintético no indica que la lectura aumenta el rendimiento en 12.5 puntos."


def start(client, sources=True):
    target = extracted(client, "afirmacion.txt", FACT)
    source = extracted(client, "fuente-sintetica.txt", NEGATION)
    r = client.post(
        "/api/v1/claims",
        json={"document_id": target["id"], "source_document_ids": [source["id"]] if sources else []},
        headers={"Idempotency-Key": "synthetic-claim"},
    )
    assert r.status_code == 202, r.text
    return "/api/v1/claims/" + r.json()["id"], target, source


def completed(client, seed):
    login(client, tenant=seed["a"])
    path, target, source = start(client)
    assert jobs.process_next()
    r = client.get(path).json()
    assert r["state"] == "completed", r
    claim = client.get(path + "/items").json()["items"][0]
    return path, target, source, claim


def passage(claim):
    c = claim["evidence"]["candidates"][0]
    return {
        "source_id": c["source_id"],
        **{
            k: c["span"][k] for k in ["fragment_id", "original_start", "original_end", "fragment_sha256", "span_sha256"]
        },
    }


def test_engine_negation_and_exact_text_never_assess_truth():
    for source in [FACT, NEGATION]:
        result = analyze(parts(FACT), [{"id": "source", "fragments": parts(source)}])
        assert len(result["claims"]) == 1
        c = result["claims"][0]
        assert c["automatic_verdict"] == "not_assessed"
        assert c["candidates"][0]["span"]["text"] == source
        assert c["span"]["text"] == FACT
        assert "12.5" in c["span"]["text"]
        assert c["span"]["span_sha256"] == digest(FACT)


def test_engine_excludes_questions_references_and_unrelated_passages():
    result = analyze(
        parts(
            FACT
            + "\n\n¿La lectura aumenta realmente los resultados en 20 puntos?\n\nReferencias\n\nEl libro indica resultados mayores en 2020 y más."
        ),
        [{"id": "source", "fragments": parts("Montañas azules rodean ciudades antiguas.")}],
    )
    assert len(result["claims"]) == 1
    assert result["claims"][0]["evidence_state"] == "no_candidate_in_bounded_search"
    assert not result["claims"][0]["candidates"]
    assert analyze(parts(FACT), [])["claims"][0]["evidence_state"] == "no_selected_sources"


def test_engine_limits_are_explicit():
    result = analyze(parts("\n\n".join([FACT] * 101)), [])
    assert result["partial"] and len(result["claims"]) == 100
    assert "claim_budget" in result["limitations"]
    with pytest.raises(ValueError, match="claim_text_budget"):
        analyze(parts("a" * 1_000_001), [])


def test_real_worker_review_history_conflict_and_export(client, seed):
    path, _, _, claim = completed(client, seed)
    assert claim["review_state"] == "unreviewed" and claim["review_revision"] == 0
    body = {
        "expected_revision": 0,
        "state": "contradicted",
        "reason": "La negación explícita requiere evaluación contextual humana.",
        "passages": [passage(claim)],
    }
    r = client.post(path + "/items/" + claim["id"] + "/review", json=body)
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["review_revision"] == 1 and saved["review_log"][0]["passages"][0]["span"]["text"] == NEGATION
    assert client.post(path + "/items/" + claim["id"] + "/review", json=body).status_code == 409
    exported = client.get(path + "/export").json()
    assert exported["claims"][0]["review_log"] == saved["review_log"]
    assert exported["run"]["summary"]["automatic_assessments"] == 0
    assert exported["run"]["summary"]["human_reviewed"] == 1


@pytest.mark.parametrize(
    "change,status", [("empty", 422), ("hash", 409), ("range", 422), ("source", 404), ("fragment", 404)]
)
def test_review_rejects_missing_or_fabricated_evidence(client, seed, change, status):
    path, _, _, claim = completed(client, seed)
    p = passage(claim)
    if change == "hash":
        p["span_sha256"] = "0" * 64
    if change == "range":
        p["original_end"] = 10000
    if change == "source":
        p["source_id"] = str(uuid.uuid4())
    if change == "fragment":
        p["fragment_id"] = str(uuid.uuid4())
    body = {
        "expected_revision": 0,
        "state": "supported",
        "reason": "Motivo humano con suficiente detalle.",
        "passages": [] if change == "empty" else [p],
    }
    assert client.post(path + "/items/" + claim["id"] + "/review", json=body).status_code == status
    assert client.get(path + "/items/" + claim["id"]).json()["review_revision"] == 0


def test_manual_unicode_span_and_no_source_uncertainty(client, seed):
    login(client, tenant=seed["a"])
    path, _, _ = start(client, sources=False)
    assert jobs.process_next()
    f = client.get(path + "/fragments").json()["items"][0]
    quote = f["original"][:10]
    body = {
        "fragment_id": f["id"],
        "original_start": 0,
        "original_end": 10,
        "fragment_sha256": f["fragment_sha256"],
        "span_sha256": digest(quote),
    }
    r = client.post(path + "/items", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["evidence"]["span"]["text"] == quote
    item = r.json()
    r = client.post(
        path + "/items/" + item["id"] + "/review",
        json={
            "expected_revision": 0,
            "state": "insufficient_source",
            "reason": "No se seleccionaron fuentes para esta evaluación.",
        },
    )
    assert r.status_code == 200 and r.json()["review_state"] == "insufficient_source"


def test_idempotency_and_cancellation_during_computation(client, seed, monkeypatch):
    login(client, tenant=seed["a"])
    path, target, source = start(client)
    body = {"document_id": target["id"], "source_document_ids": [source["id"]]}
    assert (
        client.post("/api/v1/claims", json=body, headers={"Idempotency-Key": "synthetic-claim"}).json()["id"]
        == path.rsplit("/", 1)[1]
    )
    assert (
        client.post(
            "/api/v1/claims", json={"document_id": target["id"]}, headers={"Idempotency-Key": "synthetic-claim"}
        ).status_code
        == 409
    )
    original = jobs.analyze

    def cancel(*args):
        assert client.post(path + "/cancel").status_code == 200
        return original(*args)

    monkeypatch.setattr(jobs, "analyze", cancel)
    assert jobs.process_next()
    assert client.get(path).json()["state"] == "cancelled"
    assert client.get(path + "/items").json()["items"] == []


def test_source_deletion_invalidates_all_evidence(client, seed):
    path, _, source, _ = completed(client, seed)
    assert client.delete("/api/v1/documents/" + source["id"]).status_code == 204
    for suffix in ["", "/items", "/fragments", "/export"]:
        assert client.get(path + suffix).status_code == 404
    assert client.get("/api/v1/claims").json()["items"] == []


def test_other_tenant_cannot_read_or_submit_claims(client, seed):
    path, target, _, _ = completed(client, seed)
    login(client, user="outsider", tenant=seed["b"])
    assert client.get(path).status_code == 404
    assert client.post("/api/v1/claims", json={"document_id": target["id"]}).status_code == 404
    assert client.get("/api/v1/claims").json()["items"] == []


def owner_engine():
    import os
    from sqlalchemy import create_engine

    return create_engine(os.environ["MIGRATION_DATABASE_URL"])


def test_student_cannot_review_own_run(client, seed):
    login(client, user="student", tenant=seed["a"])
    path, _, _ = start(client)
    assert jobs.process_next()
    claim = client.get(path + "/items").json()["items"][0]
    assert (
        client.post(
            path + "/items/" + claim["id"] + "/review",
            json={
                "expected_revision": 0,
                "state": "not_verifiable",
                "reason": "El estudiante no debe evaluar este resultado.",
            },
        ).status_code
        == 403
    )
    p = passage(claim)
    p.pop("source_id")
    assert client.post(path + "/items", json=p).status_code == 403


@pytest.mark.parametrize("during", [False, True])
def test_revoked_requester_cannot_publish(client, seed, monkeypatch, during):
    from sqlalchemy import text

    login(client, tenant=seed["a"])
    path, _, _ = start(client)
    owner = owner_engine()

    def revoke():
        with owner.begin() as db:
            db.execute(text("UPDATE memberships SET active=false WHERE id=:id"), {"id": seed["ma"]})

    if during:
        original = jobs.analyze

        def compute(*args):
            revoke()
            return original(*args)

        monkeypatch.setattr(jobs, "analyze", compute)
    else:
        revoke()
    assert jobs.process_next()
    with owner.connect() as db:
        assert db.execute(text("SELECT state,error_code FROM claim_runs")).one() == ("failed", "permission_revoked")
        assert db.execute(text("SELECT count(*) FROM claims")).scalar() == 0
    owner.dispose()


def test_expired_job_fails_after_three_attempts(client, seed):
    from sqlalchemy import text

    login(client, tenant=seed["a"])
    path, _, _ = start(client)
    owner = owner_engine()
    with owner.begin() as db:
        db.execute(text("UPDATE claim_jobs SET state='running',attempts=3,lease_until=now()-interval '1 minute'"))
    assert not jobs.process_next()
    assert client.get(path).json()["error_code"] == "worker_retries_exhausted"
    assert not client.get(path + "/items").json()["items"]
    owner.dispose()


def test_source_permission_loss_filters_run_before_pagination(client, seed):
    from sqlalchemy import text

    login(client, user="teacher", tenant=seed["a"])
    path, _, source = start(client)
    assert jobs.process_next()
    owner = owner_engine()
    with owner.begin() as db:
        db.execute(text("UPDATE documents SET owner_id=:owner WHERE id=:id"), {"owner": seed["ma"], "id": source["id"]})
    for suffix in ["", "/items", "/fragments", "/export"]:
        assert client.get(path + suffix).status_code == 404
    assert client.get("/api/v1/claims?limit=1").json()["items"] == []
    owner.dispose()


def test_short_body_limit_and_no_self_source(client, seed):
    login(client, tenant=seed["a"])
    doc = extracted(client, "principal.txt", FACT)
    assert (
        client.post("/api/v1/claims", json={"document_id": doc["id"], "source_document_ids": [doc["id"]]}).status_code
        == 422
    )
    assert (
        client.post("/api/v1/claims", content="x" * 65537, headers={"Content-Type": "application/json"}).status_code
        == 413
    )


def test_large_target_skips_citation_budget_without_inventing_context():
    result = analyze(parts(FACT + "\n\n" + "z" * 500_000), [])
    assert result["partial"] and result["claims"][0]["span"]["text"] == FACT
    assert result["claims"][0]["citation_context"] == []
    assert "citation_context_text_budget" in result["limitations"]
