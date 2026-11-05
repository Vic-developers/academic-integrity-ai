import pytest
import hashlib
import os
import uuid
from datetime import timedelta
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.audits import engine as literal
from app.audits.engine import compare, fingerprints, tokenize
from app.audits.jobs import process_next
from app.audits.models import AuditJob, Finding
from app.db import context, engine
from app.documents.jobs import process_next as process_document
from app.documents.normalization import fragment
from app.security import now
from conftest import login

PHRASE = "La investigación académica exige evidencia verificable y revisión humana responsable."


def parts(text):
    return [{"id": str(uuid.uuid4()), **fragment(value, i + 1)} for i, value in enumerate(text.split("\n\n"))]


def extracted(client, name, content):
    response = client.post("/api/v1/documents", files={"files": (name, content.encode(), "text/plain")})
    assert response.status_code == 202, response.text
    item = response.json()["items"][0]
    assert process_document()
    assert client.get("/api/v1/documents/" + item["id"]).json()["state"] == "completed"
    return item


def pair(client):
    a = extracted(client, "principal.txt", "Preámbulo singular. " + PHRASE + "\n\nCierre particular.")
    b = extracted(client, "fuente.txt", "Apertura distinta. " + PHRASE + "\n\nFinal diferente.")
    return a, b


def start(client, a, b, **extra):
    response = client.post("/api/v1/audits", json={"document_id": a["id"], "source_document_ids": [b["id"]], **extra})
    assert response.status_code == 202, response.text
    return response.json()


def test_winnowing_uses_rightmost_minimum_and_checks_real_tokens(monkeypatch):
    tokens = tokenize(parts(" ".join(["a"] * 12)))
    assert [position for hash, position in fingerprints(tokens)] == list(range(3, 8))
    monkeypatch.setattr(literal, "gram_hash", lambda values: 0)
    result = compare(
        parts("alpha beta gamma delta epsilon zeta eta theta iota"),
        [{"id": "different", "fragments": parts("uno dos tres cuatro cinco seis siete ocho nueve")}],
    )
    assert result["findings"] == []


def test_match_spans_paragraphs_and_preserves_unicode_words():
    target = parts("Árbol ß ﬁ uno dos\n\ntres cuatro cinco seis siete ocho")
    source = parts("árbol ss fi uno dos tres cuatro cinco seis siete ocho")
    result = compare(target, [{"id": "source", "fragments": source}])
    assert len(result["findings"]) == 1
    assert result["summary"]["matched_words"] == 11
    match = result["findings"][0]
    qt = tokenize(target)[match["target_start"] : match["target_end"]]
    st = tokenize(source)[match["source_start"] : match["source_end"]]
    assert [t.value for t in qt] == [t.value for t in st]


def test_short_text_and_budget_exhaustion_are_not_negative_verdicts():
    assert compare(parts("solo tres palabras"), [])["partial_reason"] == "target_below_minimum_words"
    result = compare(
        parts(" ".join(["palabra"] * 30)), [{"id": "a", "fragments": parts(" ".join(["palabra"] * 30))}], max_seeds=1
    )
    assert result["partial_reason"] == "seed_budget"
    assert result["sources"][0]["state"] == "partial"
    assert result["summary"]["matched_words"] <= 30


def test_union_not_double_counted_with_two_identical_sources():
    target = parts(PHRASE)
    result = compare(target, [{"id": id, "fragments": parts(PHRASE)} for id in ["one", "two"]])
    assert len(result["findings"]) == 2
    assert result["summary"]["matched_words"] == result["summary"]["target_words"] == 10


def test_punctuation_change_is_not_a_literal_normalized_match():
    result = compare(
        parts("uno dos tres, cuatro cinco seis siete ocho"),
        [{"id": "source", "fragments": parts("uno dos tres; cuatro cinco seis siete ocho")}],
    )
    assert result["findings"] == []


def test_real_audit_sources_ranges_hashes_and_counts(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert audit["state"] == "pending"
    assert process_next()
    result = client.get("/api/v1/audits/" + audit["id"]).json()
    assert result["state"] == "completed", result
    assert result["summary"]["matched_words"] == 10
    assert result["coverage"]["local"]["sources_compared"] == 1
    assert result["coverage"]["web"]["state"] == "not_requested"
    assert result["sources"][0]["sha256"] == b["sha256"]
    findings = client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"]
    assert findings
    for finding in findings:
        evidence = finding["evidence"]
        assert evidence["citation"] == "pending_review"
        assert finding["review_state"] == "pending"
        for document, side in [(a, "target_ranges"), (b, "source_ranges")]:
            by_id = {f["id"]: f for f in client.get(f"/api/v1/documents/{document['id']}/fragments").json()["items"]}
            for span in evidence[side]:
                original = by_id[span["fragment_id"]]["original"][span["original_start"] : span["original_end"]]
                assert original == span["text"]
                assert hashlib.sha256(original.encode()).hexdigest() == span["span_sha256"]


def test_requested_web_is_explicitly_unavailable_without_sources(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b, request_web=True)
    assert process_next()
    result = client.get("/api/v1/audits/" + audit["id"]).json()
    assert result["state"] == "partial"
    web = result["coverage"]["web"]
    assert (
        web["state"] == "unavailable"
        and web["queries_sent"] == web["sources_verified"] == web["sources_retrieved"] == 0
    )
    assert result["summary"]["findings"] >= 1


def test_idempotent_request_replays_and_conflicting_key_rejected(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    body = {"document_id": a["id"], "source_document_ids": [b["id"]]}
    first = client.post("/api/v1/audits", json=body, headers={"Idempotency-Key": "request-1"})
    second = client.post("/api/v1/audits", json=body, headers={"Idempotency-Key": "request-1"})
    assert first.status_code == second.status_code == 202 and first.json()["id"] == second.json()["id"]
    assert (
        client.post(
            "/api/v1/audits", json={**body, "request_web": True}, headers={"Idempotency-Key": "request-1"}
        ).status_code
        == 409
    )


def test_foreign_institution_and_same_tenant_hidden_sources_are_rejected(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert process_next()
    client.cookies.clear()
    login(client, "student", seed["a"])
    own = extracted(client, "own.txt", PHRASE)
    assert client.get("/api/v1/audits/" + audit["id"]).status_code == 404
    assert client.get(f"/api/v1/audits/{audit['id']}/findings").status_code == 404
    assert (
        client.post("/api/v1/audits", json={"document_id": own["id"], "source_document_ids": [b["id"]]}).status_code
        == 404
    )
    client.cookies.clear()
    login(client, "outsider", seed["b"])
    assert client.get("/api/v1/audits/" + audit["id"]).status_code == 404
    assert client.get("/api/v1/audits").json()["items"] == []
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM findings")).scalar_one() == 0


def test_source_deletion_invalidates_and_removes_derivative_evidence(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert process_next()
    assert client.delete("/api/v1/documents/" + b["id"]).status_code == 204
    assert client.get("/api/v1/audits/" + audit["id"]).status_code == 404
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        assert db.scalar(select(Finding)) is None
        assert (
            db.execute(text("SELECT state FROM audits WHERE id=:id"), {"id": audit["id"]}).scalar_one() == "invalidated"
        )


def test_cancel_pending_and_running_result_is_not_committed(client, seed, monkeypatch):
    from app.audits import jobs

    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    original = jobs.run_engine

    def compare_then_cancel(payload):
        result = original(payload)
        assert client.post(f"/api/v1/audits/{audit['id']}/cancel", json={}).status_code == 200
        return result

    monkeypatch.setattr(jobs, "run_engine", compare_then_cancel)
    assert process_next()
    assert client.get("/api/v1/audits/" + audit["id"]).json()["state"] == "cancelled"
    assert client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"] == []


def test_async_permissions_rechecked_after_request(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE memberships SET active=false WHERE id=:id"), {"id": seed["ma"]})
    owner.dispose()
    assert process_next()
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        assert db.execute(text("SELECT state FROM audits WHERE id=:id"), {"id": audit["id"]}).scalar_one() == "failed"
        assert db.scalar(select(Finding)) is None


def test_audit_request_size_cap_and_unready_document(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "a.txt", PHRASE)
    pending = client.post("/api/v1/documents", files={"files": ("b.txt", PHRASE.encode())}).json()["items"][0]
    assert (
        client.post("/api/v1/audits", json={"document_id": a["id"], "source_document_ids": [pending["id"]]}).status_code
        == 409
    )
    response = client.post("/api/v1/audits", content=b" " * 66000, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_expired_audit_worker_lease_recovers(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT * FROM public.claim_audit_job('old-worker')")).first()
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(
            text("UPDATE audit_jobs SET lease_until=:expiry WHERE audit_id=:id"),
            {"expiry": now() - timedelta(minutes=1), "id": audit["id"]},
        )
    owner.dispose()
    assert process_next()
    assert client.get("/api/v1/audits/" + audit["id"]).json()["state"] == "completed"
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        assert db.scalar(select(AuditJob)).attempts == 2


def test_search_snippet_is_never_verified_page_evidence():
    from app.audits.providers import SearchResult, web_coverage

    class FixtureProvider:
        def search(self, queries):
            return SearchResult(
                "completed",
                "test-only",
                len(queries),
                ({"url": "https://example.org/fixture", "snippet": "Synthetic test excerpt"},),
            )

    result = web_coverage(True, parts(PHRASE), FixtureProvider())
    assert result["state"] == "discovery_only"
    assert result["results_returned"] == 1
    assert result["sources_retrieved"] == result["sources_verified"] == 0


def test_completed_audit_access_revoked_after_role_change(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert process_next()
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE memberships SET role='student' WHERE id=:id"), {"id": seed["ma"]})
        # Move only the source ownership to another same-tenant member using operator privileges.
        conn.execute(text("UPDATE documents SET owner_id=:owner WHERE id=:id"), {"owner": seed["ms"], "id": b["id"]})
    owner.dispose()
    assert client.get("/api/v1/audits/" + audit["id"]).status_code == 404
    assert client.get(f"/api/v1/audits/{audit['id']}/findings").status_code == 404
    assert client.get("/api/v1/audits").json()["items"] == []


def test_budgets_produce_partial_and_retained_results_are_real(client, seed, monkeypatch):
    from app.config import settings

    login(client, tenant=seed["a"])
    a, b = pair(client)
    monkeypatch.setattr(settings(), "max_literal_findings", 0)
    audit = start(client, a, b)
    assert process_next()
    result = client.get("/api/v1/audits/" + audit["id"]).json()
    assert result["state"] == "partial" and result["error_code"] == "findings_budget"
    assert result["summary"]["matched_words"] == result["summary"]["findings"] == 0


def test_same_document_and_empty_sources_cannot_create_audit(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "single.txt", PHRASE)
    assert (
        client.post("/api/v1/audits", json={"document_id": a["id"], "source_document_ids": [a["id"]]}).status_code
        == 422
    )
    assert client.post("/api/v1/audits", json={"document_id": a["id"], "source_document_ids": []}).status_code == 422


def test_simultaneous_idempotent_requests_create_only_one_job(client, seed):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from app.main import app

    login(client, tenant=seed["a"])
    a, b = pair(client)
    cookies = dict(client.cookies)
    headers = {
        "Origin": "http://localhost:5173",
        "X-Requested-With": "AcademicIntegrityAI",
        "X-CSRF-Token": client.cookies["aid_csrf"],
        "Idempotency-Key": "parallel-request",
    }
    body = {"document_id": a["id"], "source_document_ids": [b["id"]]}

    def submit(_):
        with TestClient(app, headers=headers, cookies=cookies) as other:
            response = other.post("/api/v1/audits", json=body)
            assert response.status_code == 202, response.text
            return response.json()["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit, range(2)))
    assert len(set(ids)) == 1
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        assert db.execute(text("SELECT count(*) FROM audit_jobs")).scalar_one() == 1


def test_evidence_contract_rejects_fabricated_word_count_and_empty_spans():
    from app.audits.evidence import make_evidence

    q = parts(PHRASE)
    s = parts(PHRASE)
    result = compare(q, [{"id": "s", "fragments": s}])["findings"][0]
    with pytest.raises(ValueError):
        make_evidence(q, s, {**result, "words": 999})
    with pytest.raises(ValueError):
        make_evidence(q, s, {**result, "target_end": 0})
