"""Position, version and human-review regressions; real extraction/SQL where applicable."""

import hashlib
import uuid
from sqlalchemy import create_engine, text
import os
from app.audits.jobs import process_next
from app.audits.viewer import boxes
from app.documents.jobs import process_next as process_document
from conftest import login
from test_literal import pair, start, extracted
from document_fixtures import pdf_bytes


def ready(client, seed):
    login(client, tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert process_next()
    finding = client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"][0]
    return a, b, f"/api/v1/audits/{audit['id']}/findings/{finding['id']}"


def test_original_context_unicode_and_hashes(client, seed):
    login(client, tenant=seed["a"])
    a = extracted(client, "unicode.txt", "🧭 Prefacio. Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho. Cierre.")
    b = extracted(client, "normalizado.txt", "árbol ss fi uno dos tres cuatro cinco seis siete ocho")
    audit = start(client, a, b)
    assert process_next()
    f = client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"][0]
    url = f"/api/v1/audits/{audit['id']}/findings/{f['id']}"
    view = client.get(url + "/view").json()
    span = view["selected_range"]
    value = view["fragment"]["original"][span["original_start"] : span["original_end"]]
    assert value == "Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho"
    assert hashlib.sha256(value.encode()).hexdigest() == span["span_sha256"]
    assert view["highlights"][0]["start"] == len("🧭 Prefacio. ")
    assert client.get(url + "/view?range_index=-1").status_code == 422
    assert client.get(url + "/view?range_index=99").status_code == 422
    assert client.get(url + "/view?side=arbitrary").status_code == 422


def test_viewer_versions_originals_and_scope(client, seed):
    a, b, url = ready(client, seed)
    target = client.get(url + "/view").json()
    source = client.get(url + "/view?side=source").json()
    assert target["document"]["sha256"] == a["sha256"]
    assert source["document"]["sha256"] == b["sha256"]
    for side, expected in [("target", a), ("source", b)]:
        content = client.get(url + "/original?side=" + side)
        assert content.status_code == 200
        assert hashlib.sha256(content.content).hexdigest() == expected["sha256"]
    assert client.get(url.replace(url.split("/")[-1], str(uuid.uuid4())) + "/view").status_code == 404
    login(client, user="outsider", tenant=seed["b"])
    assert client.get(url + "/view").status_code == 404
    assert client.get(url + "/original").status_code == 404


def test_view_revalidates_fragment_integrity(client, seed):
    _, _, url = ready(client, seed)
    view = client.get(url + "/view").json()
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(
            text("UPDATE document_fragments SET original='texto modificado' WHERE id=:id"),
            {"id": view["fragment"]["id"]},
        )
    owner.dispose()
    assert client.get(url + "/view").status_code == 409


def test_pdf_character_geometry_exact_and_original_unchanged(client, seed):
    login(client, tenant=seed["a"])
    raw = pdf_bytes(pages=1)
    response = client.post("/api/v1/documents", files={"files": ("posicion.pdf", raw, "application/pdf")})
    pdf = response.json()["items"][0]
    assert process_document()
    src = extracted(client, "fuente.txt", "Evidence on page 1. Academic document. extra matching words here")
    # Original fixture has only seven words: extend with a second identical PDF line via a generated PDF.
    import io
    from reportlab.pdfgen import canvas

    out = io.BytesIO()
    doc = canvas.Canvas(out)
    doc.drawString(40, 750, "prefix La evidencia verificable exige una revision humana responsable ahora suffix")
    doc.save()
    raw = out.getvalue()
    pdf = client.post("/api/v1/documents", files={"files": ("posicion-larga.pdf", raw, "application/pdf")}).json()[
        "items"
    ][0]
    assert process_document()
    src = extracted(client, "fuente-larga.txt", "La evidencia verificable exige una revision humana responsable ahora")
    audit = start(client, pdf, src)
    assert process_next()
    finding = client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"][0]
    url = f"/api/v1/audits/{audit['id']}/findings/{finding['id']}"
    view = client.get(url + "/view").json()
    selected = view["highlights"][0]
    assert selected["boxes"] and len(selected["boxes"]) == sum(not c.isspace() for c in view["selected_range"]["text"])
    assert min(b[0] for b in selected["boxes"]) > 40
    assert view["page_geometry"]["rotation"] == 0
    assert client.get(url + "/original").content == raw


def test_geometry_never_guesses_missing_or_partial_glyphs():
    original = "ﬁx"
    loc = [
        {
            "kind": "pdf_word",
            "start": 0,
            "end": 2,
            "char_mapping_reliable": True,
            "chars": [{"text": "ﬁx", "bbox": [1, 2, 9, 8]}],
        }
    ]
    assert boxes(original, loc, 0, 1) is None
    assert boxes(original, loc, 0, 2) == [[1, 2, 9, 8]]
    assert boxes("abc", [], 0, 3) is None
    loc[0]["char_mapping_reliable"] = False
    assert boxes(original, loc, 0, 2) is None


def test_human_review_history_conflict_and_reason(client, seed):
    _, _, url = ready(client, seed)
    body = {
        "expected_revision": 0,
        "state": "justified",
        "citation": "correct",
        "reason": "Coincidencia citada con contexto adecuado.",
    }
    r = client.post(url + "/review", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["review_revision"] == 1
    assert r.json()["review_log"][0]["actor_id"] == seed["ma"]
    assert client.post(url + "/review", json=body).status_code == 409
    assert client.post(url + "/review", json={**body, "expected_revision": 1, "reason": "     "}).status_code == 422
    assert client.post(url + "/review", json={**body, "expected_revision": 1, "state": "guilty"}).status_code == 422
    r = client.post(
        url + "/review",
        json={
            **body,
            "expected_revision": 1,
            "state": "dismissed",
            "reason": "Rango descartado por contexto de la actividad.",
        },
    )
    assert r.status_code == 200
    assert len(r.json()["review_log"]) == 2
    view = client.get(url + "/view").json()
    assert view["highlights"][0]["review_state"] == "dismissed"


def test_student_cannot_record_review_even_for_own_audit(client, seed):
    login(client, user="student", tenant=seed["a"])
    a, b = pair(client)
    audit = start(client, a, b)
    assert process_next()
    finding = client.get(f"/api/v1/audits/{audit['id']}/findings").json()["items"][0]
    url = f"/api/v1/audits/{audit['id']}/findings/{finding['id']}"
    assert client.get(url + "/view").status_code == 200
    assert (
        client.post(
            url + "/review",
            json={"expected_revision": 0, "state": "confirmed", "reason": "Intento de validar mi propia coincidencia."},
        ).status_code
        == 403
    )


def test_deleted_source_closes_view_original_and_review(client, seed):
    _, b, url = ready(client, seed)
    assert client.delete("/api/v1/documents/" + b["id"]).status_code == 204
    assert client.get(url + "/view").status_code == 404
    assert client.get(url + "/original").status_code == 404
    assert (
        client.post(
            url + "/review",
            json={"expected_revision": 0, "state": "reviewed", "reason": "No debe poder guardarse tras el borrado."},
        ).status_code
        == 404
    )


def test_export_contains_real_provenance_and_review_with_permission_recheck(client, seed):
    a, b, url = ready(client, seed)
    response = client.get(url + "/export")
    assert response.status_code == 200
    data = response.json()
    assert data["target"]["sha256"] == a["sha256"]
    assert data["source"]["sha256"] == b["sha256"]
    assert data["evidence"]["offset_unit"] == "unicode_code_points"
    assert data["review_revision"] == 0 and data["review_log"] == []
    assert "attachment;" in response.headers["content-disposition"]
    login(client, user="outsider", tenant=seed["b"])
    assert client.get(url + "/export").status_code == 404
