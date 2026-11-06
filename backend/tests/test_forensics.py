import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from app.forensics.engine import analyze, style_comparison, display
from app.documents.extractor import extract_docx, extract_pdf
from app.claims.engine import digest
from conftest import login
from test_literal import extracted, parts


def test_unicode_flags_original_hashes_bidi_and_budget():
    raw = "🧭 pala\u200bbra con aа y ﬁnal.\u202e Cierre."
    result = analyze(parts(raw), {"Author": "Nombre\u202e contextual"}, None)
    assert result["counts"]["format_or_control_character"] == 2
    assert result["counts"]["mixed_letter_scripts"] == 1
    assert result["counts"]["compatibility_normalization"] == 1
    for flag in result["flags"]:
        span = flag["span"]
        assert raw[span["original_start"] : span["original_end"]] == span["text"]
        assert digest(span["text"]) == span["span_sha256"]
    assert "\u202e" not in result["metadata"][0]["display_value"]
    assert "\\u202E" in result["metadata"][0]["display_value"]
    assert display("\u200b") == "\\u200B"
    many = analyze(parts("x\u200b" * 300), {}, None)
    assert many["partial"] and many["flags_total"] == 300 and many["flags_returned"] == 250
    assert result["authorship_probability"] is None


def test_dates_editable_metadata_and_missing_format_inspection():
    result = analyze(parts("Texto normal."), {"created": "2020-02-01", "modified": "2019-01-01"}, "old-extractor")
    assert result["date_observation"] == "modified_before_created"
    assert not result["format_inspection_available"]
    assert "metadata_is_editable_context_not_authorship_proof" in result["limitations"]
    for dates in [
        {"CreationDate": "D:20200101000000Z", "ModDate": "D:20220101000000Z"},
        {"created": "incorrecto", "modified": "ayer"},
    ]:
        r = analyze(parts("Texto."), dates, None)
        assert r["date_observation"] in {"no_reversal_in_parsed_dates", "not_compared"}


def test_docx_real_declared_hidden_white_tiny_text_and_metadata(tmp_path):
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    doc.core_properties.author = "Autor registrado de prueba"
    p = doc.add_paragraph("Visible. ")
    run = p.add_run("Texto de muestra oculto")
    run.font.hidden = True
    run.font.color.rgb = RGBColor(255, 255, 255)
    run.font.size = Pt(1)
    path = tmp_path / "forense.docx"
    doc.save(path)
    extracted_doc = extract_docx(path)
    data = [{"id": str(uuid.uuid4()), **f} for f in extracted_doc["fragments"]]
    result = analyze(data, extracted_doc["metadata"], extracted_doc["extractor"])
    assert result["counts"]["explicit_hidden_run"] == 1
    assert result["counts"]["white_text_color"] == 1 and result["counts"]["font_size_at_most_2pt"] == 1
    assert result["format_inspection_available"]
    assert any(f["name"] == "author" and f["value"] == "Autor registrado de prueba" for f in result["metadata"])
    assert all(f["span"]["text"] == "Texto de muestra oculto" for f in result["flags"])


def test_real_pdf_white_and_small_font_observations(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "forense.pdf"
    c = canvas.Canvas(str(path))
    c.setAuthor("Autor PDF contextual")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 1)
    c.drawString(60, 700, "White text sample")
    c.save()
    value = extract_pdf(path)
    result = analyze(
        [{"id": str(uuid.uuid4()), **f} for f in value["fragments"]], value["metadata"], value["extractor"]
    )
    assert result["counts"]["white_text_color"] >= 1 and result["counts"]["font_size_at_most_2pt"] >= 1
    assert "white_text_can_be_visible_on_colored_background" in result["limitations"]


def attestation_body(day="2024-01-01", verified=True, revision=0, **changes):
    return {
        "expected_revision": revision,
        "verified_writing_sample": verified,
        "authorization_reference": "Consentimiento de prueba documental explícito",
        "provenance_reference": "Muestra anterior verificada por evaluador de prueba",
        "language": "es",
        "domain": "ensayo",
        "genre": "prosa",
        "sample_date": day,
        "reason": "Registro técnico de autorización y procedencia.",
        **changes,
    }


def style_setup(client, seed):
    login(client, user="student", tenant=seed["a"])
    docs = []
    for i in range(3):
        content = " ".join(f"palabra{i}tema{k}" for k in range(110 + i * 2)) + "."
        docs.append(extracted(client, f"muestra-{i}.txt", content))
    login(client, tenant=seed["a"])
    for i, d in enumerate(docs):
        r = client.post(
            "/api/v1/forensics/documents/" + d["id"] + "/attestation",
            json=attestation_body(day="2025-01-01" if i == 0 else "2024-01-01", verified=i != 0),
        )
        assert r.status_code == 200, r.text
    return docs, {
        "document_id": docs[0]["id"],
        "source_document_ids": [d["id"] for d in docs[1:]],
        "expected_revisions": {d["id"]: 1 for d in docs},
    }


def test_authorized_descriptive_comparison_and_revision_conflict(client, seed):
    docs, body = style_setup(client, seed)
    result = client.post("/api/v1/forensics/style/compare", json=body)
    assert result.status_code == 200, result.text
    payload = result.json()
    assert len(payload["comparison"]["rows"]) == 8
    assert payload["comparison"]["assessment"] == "descriptive_comparison_only"
    assert payload["comparison"]["authorship_probability"] is None
    path = "/api/v1/forensics/documents/" + docs[1]["id"] + "/attestation"
    r = client.post(path, json=attestation_body(revision=1, active=False))
    assert r.status_code == 200 and len(r.json()["history"]) == 2
    assert client.post(path, json=attestation_body(revision=1)).status_code == 409
    assert client.post("/api/v1/forensics/style/compare", json=body).status_code == 409


@pytest.mark.parametrize("change", ["unverified", "domain", "date", "student", "short", "duplicate"])
def test_invalid_style_samples_do_not_produce_findings(client, seed, change):
    docs, body = style_setup(client, seed)
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    if change in {"unverified", "domain", "date"}:
        options = {"unverified": {"verified": False}, "domain": {"domain": "otro"}, "date": {"day": "2025-01-02"}}[
            change
        ]
        r = client.post(
            "/api/v1/forensics/documents/" + docs[1]["id"] + "/attestation",
            json=attestation_body(revision=1, **options),
        )
        assert r.status_code == 200
        body["expected_revisions"][docs[1]["id"]] = 2
    else:
        with owner.begin() as db:
            if change == "student":
                db.execute(
                    text("UPDATE documents SET owner_id=:id WHERE id=:doc"), {"id": seed["ma"], "doc": docs[1]["id"]}
                )
            if change == "short":
                db.execute(
                    text(
                        "UPDATE document_fragments SET original='Texto corto' WHERE version_id=(SELECT id FROM document_versions WHERE document_id=:doc)"
                    ),
                    {"doc": docs[1]["id"]},
                )
            if change == "duplicate":
                db.execute(
                    text(
                        "UPDATE document_fragments SET original=(SELECT original FROM document_fragments WHERE version_id=(SELECT id FROM document_versions WHERE document_id=:target) LIMIT 1) WHERE version_id=(SELECT id FROM document_versions WHERE document_id=:doc)"
                    ),
                    {"target": docs[0]["id"], "doc": docs[1]["id"]},
                )
    response = client.post("/api/v1/forensics/style/compare", json=body)
    assert response.status_code in {409, 422}, response.text
    owner.dispose()


def test_forensic_read_tenant_student_permissions_and_deletion(client, seed):
    login(client, user="student", tenant=seed["a"])
    doc = extracted(client, "invisible.txt", "Texto con\u200b carácter contextual.")
    path = "/api/v1/forensics/documents/" + doc["id"]
    result = client.get(path)
    assert result.status_code == 200 and result.json()["observation"]["flags_total"] == 1
    assert client.post(path + "/attestation", json=attestation_body()).status_code == 403
    login(client, user="teacher", tenant=seed["a"])
    assert client.get(path).status_code == 404
    login(client, user="outsider", tenant=seed["b"])
    assert client.get(path).status_code == 404
    login(client, tenant=seed["a"])
    assert client.post(path + "/attestation", json=attestation_body()).status_code == 200
    assert client.delete("/api/v1/documents/" + doc["id"]).status_code == 204
    assert client.get(path).status_code == 404
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.connect() as db:
        assert db.execute(text("SELECT count(*) FROM style_attestations")).scalar() == 0
    owner.dispose()


def test_style_minimum_and_duplicate_text_fail_closed():
    with pytest.raises(ValueError, match="below_100"):
        style_comparison("corto", ["otra", "breve"])
    value = " ".join("palabra" + str(i) for i in range(101))
    with pytest.raises(ValueError, match="duplicate_style_text"):
        style_comparison(value, [value, value])
