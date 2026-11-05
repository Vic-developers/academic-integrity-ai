"""Local extraction, real SQL/job permissions and labelled provider fixtures; not live API success."""

from dataclasses import asdict
import hashlib
import json
import os
import pytest
from sqlalchemy import create_engine, text
from app.bibliography.extraction import canonical_doi, extract
from app.bibliography.jobs import process_next
from app.bibliography.providers import Provider, compare
from conftest import login
from test_literal import extracted, parts

TEXT = "🧭 Contexto de prueba (García, 2020). Una afirmación [2] y otra [9].\n\nReferencias\n\n[1] García, A. (2020). Estudio técnico de evidencia. Revista de Pruebas. https://doi.org/10.5555/technical-fixture.\n\n[2] López, B. (2021). Otra investigación de prueba. Revista Local. doi:10.5555/other-fixture\n\n[3] García, A. (2020). Estudio técnico de evidencia. Revista de Pruebas. DOI:10.5555/TECHNICAL-FIXTURE\n\nAnexos\n\nEste texto ya no es una referencia."


def document(client):
    return extracted(client, "bibliografia.txt", TEXT)


def start(client, doc, **options):
    r = client.post("/api/v1/bibliography", json={"document_id": doc["id"], **options})
    assert r.status_code == 202, r.text
    return "/api/v1/bibliography/" + r.json()["id"]


def test_local_references_duplicates_citations_and_original_unicode_spans():
    fragments = parts(TEXT)
    result = extract(fragments)
    assert result["heading_found"] and len(result["references"]) == 3
    ref = result["references"][0]
    assert ref["fields"]["dois"] == ["10.5555/technical-fixture"]
    assert ref["fields"]["year"] == 2020 and ref["fields"]["authors"] == "García, A."
    assert result["references"][2]["duplicate_of"] == 1
    assert any(c["state"] == "unmatched_candidate" and c["label"] == "9" for c in result["citations"])
    assert ref["citation_state"] == "seen_in_supported_pattern"
    by_id = {f["id"]: f for f in fragments}
    for item in result["references"] + result["citations"]:
        for span in item["spans"]:
            original = by_id[span["fragment_id"]]["original"][span["original_start"] : span["original_end"]]
            assert hashlib.sha256(original.encode()).hexdigest() == span["span_sha256"]


def test_doi_normalization_balancing_and_bounded_input():
    assert canonical_doi("HTTPS://DOI.ORG/10.1002/(SICI)FOO).") == "10.1002/(sici)foo"
    assert canonical_doi("10.1000/foo%20bar") == "10.1000/foo%20bar"
    assert canonical_doi("10.1000/" + ")" * 100000) is None
    assert canonical_doi("https://attacker.example/x") is None
    assert canonical_doi("10.1000/palabra con espacios") is None
    result = extract(parts("Un DOI en el cuerpo 10.5555/technical-fixture."))
    assert not result["heading_found"] and result["local_partial"]
    assert result["references"][0]["kind"] == "doi_mention"
    assert result["references"][0]["citation_state"] == "not_assessed"


def response(provider="crossref", *, doi="10.5555/technical-fixture", title="Estudio técnico de evidencia", year=2020):
    # Explicit synthetic contract data, never evidence of a live provider request.
    if provider == "crossref":
        data = {
            "status": "ok",
            "message": {
                "DOI": doi,
                "title": [title],
                "author": [{"family": "García", "given": "A."}],
                "published": {"date-parts": [[year]]},
                "container-title": ["Revista de Pruebas"],
                "publisher": "Editorial de prueba",
            },
        }
    else:
        data = {
            "doi": "https://doi.org/" + doi,
            "title": title,
            "publication_year": year,
            "authorships": [{"author": {"display_name": "A. García"}}],
            "primary_location": {"source": {"display_name": "Revista de Pruebas"}},
        }
    return json.dumps(data, ensure_ascii=False).encode()


def test_provider_preserves_actual_response_hash_and_compares_printed_fields():
    body = response()
    seen = []

    def transport(url):
        seen.append(url)
        return 200, {}, body

    result = Provider("crossref", enabled=True, transport=transport).lookup("10.5555/technical-fixture")
    assert result.state == "found" and result.attempted
    assert seen[0] == "https://api.crossref.org/works/10.5555%2Ftechnical-fixture"
    assert result.response_sha256 == hashlib.sha256(body).hexdigest()
    assert result.response_text.encode() == body and result.retrieved_at
    ref = extract(parts(TEXT))["references"][0]
    compared = compare(ref, result.metadata)
    assert compared["state"] == "partially_verified"
    assert next(x for x in compared["checks"] if x["field"] == "title")["state"] == "equal"
    wrong = Provider("crossref", enabled=True, transport=lambda url: (200, {}, response(year=2018))).lookup(
        "10.5555/technical-fixture"
    )
    assert compare(ref, wrong.metadata)["state"] == "inconsistent"


@pytest.mark.parametrize(
    "status,state",
    [
        (404, "not_found"),
        (429, "rate_limited"),
        (403, "unauthorized"),
        (503, "provider_error"),
        (302, "provider_error"),
    ],
)
def test_provider_http_failures_never_become_verified(status, state):
    result = Provider(
        "crossref",
        enabled=True,
        transport=lambda url: (status, {"Retry-After": "9999"}, b"error with secret request URL"),
    ).lookup("10.5555/technical-fixture")
    assert result.state == state and result.metadata is None and result.response_text is None
    if status == 429:
        assert result.retry_after == 3600


def test_invalid_and_oversized_provider_responses_rejected():
    for body in [response(doi="10.5555/wrong"), b"not json", b"x" * 262145]:
        result = Provider("crossref", enabled=True, transport=lambda url: (200, {}, body)).lookup(
            "10.5555/technical-fixture"
        )
        assert result.state in {"invalid_response", "response_too_large"}
        assert result.metadata is None and result.response_text is None
    assert Provider("openalex", enabled=True).lookup("10.5555/technical-fixture").state == "not_configured"
    assert not Provider("crossref").lookup("10.5555/technical-fixture").attempted
    with pytest.raises(ValueError):
        Provider("arbitrary")


def test_openalex_key_is_not_returned_in_evidence():
    result = Provider(
        "openalex",
        enabled=True,
        api_key="technical-secret-do-not-log",
        transport=lambda url: (200, {}, response("openalex")),
    ).lookup("10.5555/technical-fixture")
    assert result.state == "found"
    assert "technical-secret" not in json.dumps(asdict(result))


def test_local_job_api_snapshot_and_idempotency(client, seed):
    login(client, tenant=seed["a"])
    doc = document(client)
    body = {"document_id": doc["id"]}
    a = client.post("/api/v1/bibliography", json=body, headers={"Idempotency-Key": "technical-replay"})
    b = client.post("/api/v1/bibliography", json=body, headers={"Idempotency-Key": "technical-replay"})
    assert a.status_code == 202 and a.json()["id"] == b.json()["id"]
    assert (
        client.post(
            "/api/v1/bibliography",
            json={**body, "request_external": True},
            headers={"Idempotency-Key": "technical-replay"},
        ).status_code
        == 409
    )
    assert process_next()
    url = "/api/v1/bibliography/" + a.json()["id"]
    run = client.get(url).json()
    assert run["state"] == "completed" and run["summary"]["references"] == 3
    assert run["summary"]["metadata_retrieved_references"] == run["summary"]["provider_attempts"] == 0
    assert run["target"]["sha256"] == doc["sha256"]
    rows = client.get(url + "/references").json()["items"]
    assert all(r["verification_state"] == "not_requested" for r in rows)
    assert client.get(url + "/export").json()["result"]["references"] == rows
    assert client.get(url + "/references/99").status_code == 404


def test_requested_but_disabled_remote_is_partial_not_verified(client, seed):
    login(client, tenant=seed["a"])
    url = start(client, document(client), request_external=True)
    assert process_next()
    run = client.get(url).json()
    assert run["state"] == "partial" and run["summary"]["provider_attempts"] == 0
    assert run["summary"]["metadata_retrieved_references"] == 0
    assert all(x["state"] == "disabled" for r in client.get(url + "/references").json()["items"] for x in r["lookups"])


def test_worker_fixture_metadata_and_dedup_never_sends_whole_reference(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    url = start(client, document(client), request_external=True, providers=["crossref"])
    calls = []

    def transport(url):
        calls.append(url)
        return 200, {}, response(doi="10.5555/other-fixture" if "other-fixture" in url else "10.5555/technical-fixture")

    assert process_next({"crossref": Provider("crossref", enabled=True, transport=transport)})
    assert len(calls) == 2 and all("Garc" not in value and "Estudio" not in value for value in calls)
    run = client.get(url).json()
    assert run["summary"]["metadata_retrieved_references"] == 3
    rows = client.get(url + "/references").json()["items"]
    assert all("response_text" not in r for ref in rows for r in ref["lookups"])
    full = client.get(url + "/references/1").json()
    assert full["provider_responses"][0]["response_text"]


def test_other_tenant_and_same_tenant_requester_privacy(client, seed):
    login(client, tenant=seed["a"])
    url = start(client, document(client))
    assert process_next()
    login(client, user="outsider", tenant=seed["b"])
    assert (
        client.get(url).status_code
        == client.get(url + "/references").status_code
        == client.get(url + "/export").status_code
        == 404
    )
    assert client.get("/api/v1/bibliography").json()["items"] == []
    login(client, user="teacher", tenant=seed["a"])
    assert client.get(url).status_code == 404


def test_delete_invalidates_and_clears_cached_evidence(client, seed):
    login(client, tenant=seed["a"])
    doc = document(client)
    url = start(client, doc)
    assert process_next()
    assert client.delete("/api/v1/documents/" + doc["id"]).status_code == 204
    assert client.get(url).status_code == client.get(url + "/export").status_code == 404
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.connect() as conn:
        state, data, snapshot = conn.execute(text("SELECT state,result,target_snapshot FROM bibliography_runs")).one()
        assert state == "invalidated" and data == snapshot == {}
    owner.dispose()


def test_cancelled_run_cannot_publish_and_revoked_requester_fails(client, seed):
    login(client, tenant=seed["a"])
    doc = document(client)
    url = start(client, doc)
    assert client.post(url + "/cancel").status_code == 200
    assert not process_next()
    assert client.get(url).json()["state"] == "cancelled"
    url = start(client, doc)
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE memberships SET active=false WHERE id=:id"), {"id": seed["ma"]})
    assert process_next()
    with owner.connect() as conn:
        assert conn.execute(
            text("SELECT state,error_code FROM bibliography_runs WHERE id=:id"), {"id": url.split("/")[-1]}
        ).one() == ("failed", "permission_revoked")
    owner.dispose()


def test_validation_and_body_limits(client, seed):
    login(client, tenant=seed["a"])
    doc = document(client)
    assert (
        client.post(
            "/api/v1/bibliography", json={"document_id": doc["id"], "providers": ["http://127.0.0.1"]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/bibliography", content=b" " * 65537, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert client.get("/api/v1/bibliography?limit=0").status_code == 422


def test_one_provider_found_another_unavailable_still_reports_partial(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    url = start(client, document(client), request_external=True)
    assert process_next(
        {
            "crossref": Provider(
                "crossref",
                enabled=True,
                transport=lambda url: (
                    200,
                    {},
                    response(doi="10.5555/other-fixture" if "other-fixture" in url else "10.5555/technical-fixture"),
                ),
            ),
            "openalex": Provider("openalex"),
        }
    )
    assert client.get(url).json()["state"] == "partial"


def test_cancel_during_provider_lookup_discards_late_metadata(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    url = start(client, document(client), request_external=True, providers=["crossref"])

    def transport(_):
        client.post(url + "/cancel")
        return 200, {}, response()

    assert process_next({"crossref": Provider("crossref", enabled=True, transport=transport)})
    run = client.get(url).json()
    assert run["state"] == "cancelled" and run["summary"] == {}
    assert client.get(url + "/references").json()["items"] == []


def test_completed_result_hidden_after_document_permissions_change(client, seed):
    login(client, tenant=seed["a"])
    doc = document(client)
    url = start(client, doc)
    assert process_next()
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(text("UPDATE memberships SET role='student' WHERE id=:id"), {"id": seed["ma"]})
        conn.execute(text("UPDATE documents SET owner_id=:id WHERE id=:doc"), {"id": seed["mt"], "doc": doc["id"]})
    owner.dispose()
    assert (
        client.get(url).status_code
        == client.get(url + "/references").status_code
        == client.get(url + "/export").status_code
        == 404
    )
    assert client.get("/api/v1/bibliography?limit=1").json()["items"] == []


def test_exhausted_lease_fails_without_publishing_results(client, seed):
    login(client, tenant=seed["a"])
    url = start(client, document(client))
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(
            text("UPDATE bibliography_jobs SET state='running',attempts=3,lease_until=now()-interval '1 minute'")
        )
    assert not process_next()
    run = client.get(url).json()
    assert run["state"] == "failed" and run["error_code"] == "worker_retries_exhausted"
    owner.dispose()


def test_venue_volume_doi_case_and_first_author_do_not_overclaim_full_list():
    ref = extract(
        parts(
            "Referencias\n\nGarcía Márquez, A. (2020). Estudio técnico de evidencia. Revista de Pruebas, 12(1), 40-50. DOI:10.5555/technical-fixture"
        )
    )["references"][0]
    assert ref["fields"]["venue"] == "Revista de Pruebas"
    metadata = {
        "doi": "10.5555/technical-fixture",
        "title": "Estudio técnico de evidencia",
        "authors": ["A. García Márquez", "Otra Autora"],
        "years": [2020],
        "venue": "Revista de Pruebas",
        "publisher": None,
    }
    result = compare(ref, metadata)
    assert result["state"] == "partially_verified"
    assert next(c for c in result["checks"] if c["field"] == "authors")["state"] == "partial_equal"


def test_provider_malformed_title_is_not_interpreted_as_first_character():
    value = json.loads(response())
    value["message"]["title"] = "Malformed schema"
    lookup = Provider("crossref", enabled=True, transport=lambda url: (200, {}, json.dumps(value).encode())).lookup(
        "10.5555/technical-fixture"
    )
    assert lookup.state == "invalid_response" and lookup.metadata is None


def test_institution_policy_is_admin_only_and_revocation_cancels_pending_external(client, seed):
    login(client, user="student", tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 403
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    capabilities = client.get("/api/v1/bibliography/capabilities").json()
    assert capabilities["institution_external_allowed"] is True and capabilities["crossref_enabled"] is False
    url = start(client, document(client), request_external=True)
    assert client.post("/api/v1/bibliography/policy", json={"allowed": False}).status_code == 200
    assert client.get(url).json()["state"] == "cancelled"
    assert not process_next()
    login(client, user="outsider", tenant=seed["b"])
    assert client.get("/api/v1/bibliography/capabilities").json()["institution_external_allowed"] is False


def test_institution_revocation_stops_further_provider_requests(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    url = start(client, document(client), request_external=True, providers=["crossref"])
    calls = []

    def transport(url):
        calls.append(url)
        assert client.post("/api/v1/bibliography/policy", json={"allowed": False}).status_code == 200
        return 200, {}, response()

    assert process_next({"crossref": Provider("crossref", enabled=True, transport=transport)})
    assert len(calls) == 1
    assert client.get(url).json()["state"] == "cancelled"
    assert client.get(url + "/references").json()["items"] == []


def test_transport_child_rejects_arbitrary_destinations_before_network():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "app.bibliography.http_child"],
        input=json.dumps({"url": "http://127.0.0.1/private?api_key=synthetic-secret"}).encode(),
        capture_output=True,
        timeout=5,
    )
    assert json.loads(result.stdout) == {"network_error": True}
    assert b"synthetic-secret" not in result.stdout


def test_provider_response_echoing_api_key_is_never_retained():
    value = json.loads(response("openalex"))
    value["debug_request"] = "https://api.openalex.org/works/x?api_key=technical-secret-echo"
    result = Provider(
        "openalex",
        enabled=True,
        api_key="technical-secret-echo",
        transport=lambda url: (200, {}, json.dumps(value).encode()),
    ).lookup("10.5555/technical-fixture")
    assert result.state == "invalid_response" and result.response_text is None and result.metadata is None
    assert "technical-secret-echo" not in json.dumps(asdict(result))


def test_rate_limited_provider_is_not_called_again_for_other_dois(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/bibliography/policy", json={"allowed": True}).status_code == 200
    url = start(client, document(client), request_external=True, providers=["crossref"])
    calls = []

    def transport(url):
        calls.append(url)
        return 429, {"Retry-After": "120"}, b""

    assert process_next({"crossref": Provider("crossref", enabled=True, transport=transport)})
    assert len(calls) == 1
    assert client.get(url).json()["state"] == "partial"
    assert client.get(url).json()["summary"]["provider_attempts"] == 1
