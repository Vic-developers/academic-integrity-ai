from pathlib import Path
import hashlib
import io
import os
import subprocess
import sys
import zipfile
from datetime import timedelta
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.config import settings
from app.db import context, engine
from app.documents.jobs import process_next
from app.documents.models import DocumentJob
from app.documents.normalization import normalize, original_range
from app.documents.storage import object_path
from app.security import now
from conftest import login


from document_fixtures import pdf_bytes, docx_bytes


def upload(client, name="trabajo.txt", content=b"Texto academico verificable.", **fields):
    response = client.post(
        "/api/v1/documents", files={"files": (name, content, "application/octet-stream")}, data=fields
    )
    assert response.status_code == 202, response.text
    assert not response.json()["errors"], response.text
    return response.json()["items"][0]


@pytest.mark.parametrize("format", ["txt", "pdf", "docx"])
def test_real_file_roundtrip_extraction_mapping_and_private_original(client, seed, format):
    login(client, tenant=seed["a"])
    content = {"txt": "Árbol ß ﬁ 😃.\n\nOtro párrafo.\fPágina dos.".encode(), "pdf": pdf_bytes(), "docx": docx_bytes()}[
        format
    ]
    document = upload(client, "original." + format, content)
    assert document["state"] == "received"
    assert document["sha256"] == hashlib.sha256(content).hexdigest()
    path = object_path(seed["a"], document["version_id"])
    assert path.stat().st_mode & 0o077 == 0
    assert process_next()
    result = client.get("/api/v1/documents/" + document["id"]).json()
    assert result["state"] == "completed", result
    assert result["extractor"]
    downloaded = client.get(f"/api/v1/documents/{document['id']}/original")
    assert downloaded.content == content
    assert downloaded.headers["content-disposition"].startswith("attachment")
    assert downloaded.headers["cache-control"] == "no-store"
    fragments = client.get(f"/api/v1/documents/{document['id']}/fragments").json()["items"]
    assert fragments
    for f in fragments:
        assert len(f["mapping"]) == len(f["normalized"])
        assert all(0 <= start < end <= len(f["original"]) for start, end in f["mapping"])
        assert all(0 <= s["start"] < s["end"] <= len(f["original"]) for s in f["sentences"])
    if format == "pdf":
        assert {f["page"] for f in fragments} == {1, 2}
        for f in fragments:
            for word in f["locations"]:
                assert f["original"][word["start"] : word["end"]]
                assert word["bbox"][0] < word["bbox"][2]
        assert len(result["metadata"]["pages"]) == 2
        first = fragments[0]["locations"][0]["bbox"]
        assert first[0] == pytest.approx(40)
        baseline = result["metadata"]["pages"][0]["height"] - 750
        assert first[1] < baseline < first[3]
    elif format == "docx":
        assert result["pages"] is None
        assert any("tabla" in f["original"] for f in fragments)
        assert any("Encabezado" in f["original"] for f in fragments)
        assert any("word/document.xml" in loc.get("part", "") for f in fragments for loc in f["locations"])
    else:
        assert result["pages"] == 2
        assert fragments[0]["original"].startswith("Árbol")


def test_unicode_positions_expansion_composition_and_non_bmp():
    original = "  Á ß ﬁ 😃\u200b  "
    normalized, mapping = normalize(original)
    assert normalized == "á ss fi 😃"
    start = normalized.index("ss")
    a, b = original_range(mapping, start, start + 2)
    assert original[a:b] == "ß"
    start = normalized.index("á")
    a, b = original_range(mapping, start, start + 1)
    assert original[a:b] == "Á"
    with pytest.raises(ValueError):
        original_range(mapping, 0, 999)


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("corrupt_pdf", "invalid_pdf"),
        ("encrypted_pdf", "encrypted_pdf"),
        ("zip_traversal", "unsafe_docx"),
        ("corrupt_docx", "invalid_docx"),
    ],
)
def test_hostile_and_corrupt_files_report_specific_failures(client, seed, kind, expected):
    login(client, tenant=seed["a"])
    if kind == "corrupt_pdf":
        content, name = b"%PDF-1.7\ncorrupt", "bad.pdf"
    elif kind == "encrypted_pdf":
        content, name = pdf_bytes(encrypt="private-password"), "locked.pdf"
    elif kind == "corrupt_docx":
        content, name = b"PK\x03\x04broken", "bad.docx"
    else:
        out = io.BytesIO(docx_bytes())
        with zipfile.ZipFile(out, "a") as archive:
            archive.writestr("../outside.txt", "untrusted")
        content, name = out.getvalue(), "unsafe.docx"
    document = upload(client, name, content)
    assert process_next()
    result = client.get("/api/v1/documents/" + document["id"]).json()
    assert result["state"] == "failed" and result["error_code"] == expected, result
    assert client.get(f"/api/v1/documents/{document['id']}/original").content == content


def test_scanned_pdf_has_honest_partial_ocr_status(client, seed):
    login(client, tenant=seed["a"])
    document = upload(client, "scan.pdf", pdf_bytes(scanned=True))
    assert process_next()
    result = client.get("/api/v1/documents/" + document["id"]).json()
    assert result["state"] == "partial"
    assert any("ocr_unavailable" in w for w in result["warnings"])
    assert client.get(f"/api/v1/documents/{document['id']}/fragments").json()["items"] == []


def test_page_limit_and_file_size_enforced(client, seed, monkeypatch):
    login(client, tenant=seed["a"])
    monkeypatch.setattr(settings(), "max_pdf_pages", 1)
    document = upload(client, "large.pdf", pdf_bytes())
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["error_code"] == "page_limit"
    monkeypatch.setattr(settings(), "max_file_bytes", 4)
    response = client.post("/api/v1/documents", files={"files": ("too-big.txt", b"12345")})
    assert response.status_code == 202 and response.json()["errors"][0]["status"] == 413


def test_total_request_limit_even_with_streamed_body(client, seed, monkeypatch):
    login(client, tenant=seed["a"])
    monkeypatch.setattr(settings(), "max_request_bytes", 30)
    response = client.post("/api/v1/documents", files={"files": ("a.txt", b"x" * 50)})
    assert response.status_code == 413, response.text


def test_batch_spoofed_type_utf8_and_duplicates(client, seed):
    login(client, tenant=seed["a"])
    files = [
        ("files", ("first.txt", "Contenido válido".encode())),
        ("files", ("second.txt", "Contenido válido".encode())),
        ("files", ("spoof.pdf", b"not a pdf")),
        ("files", ("bad.txt", b"\xff\xfe")),
        ("files", ("../escape.txt", b"text")),
    ]
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 202
    body = response.json()
    assert len(body["items"]) == 2 and len(body["errors"]) == 3
    assert body["items"][1]["duplicate_of"] == body["items"][0]["id"]
    assert sorted(e["status"] for e in body["errors"]) == [415, 422, 422]


def test_cross_institution_and_owner_access_do_not_leak_hashes(client, seed):
    login(client, "student", seed["a"])
    first = upload(client)
    client.cookies.clear()
    login(client, "teacher", seed["a"])
    assert client.get("/api/v1/documents/" + first["id"]).status_code == 404
    assert client.get(f"/api/v1/documents/{first['id']}/original").status_code == 404
    second = upload(client)
    assert second["duplicate_of"] is None
    client.cookies.clear()
    login(client, "outsider", seed["b"])
    assert client.get("/api/v1/documents/" + first["id"]).status_code == 404
    third = upload(client)
    assert third["duplicate_of"] is None
    assert len(client.get("/api/v1/documents").json()["items"]) == 1
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM documents")).scalar_one() == 0
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["b"])
        assert db.execute(text("SELECT id FROM documents")).scalars().all() == [third["id"]]


def test_course_assignment_enrollment_and_teacher_access(client, seed):
    login(client, tenant=seed["a"])
    course = client.post("/api/v1/courses", json={"name": "Metodología", "teacher_id": seed["mt"]}).json()
    assignment = client.post("/api/v1/assignments", json={"course_id": course["id"], "name": "Ensayo"}).json()
    assert (
        client.post(f"/api/v1/courses/{course['id']}/enrollments", json={"student_id": seed["ms"]}).status_code == 201
    )
    client.cookies.clear()
    login(client, "student", seed["a"])
    document = upload(client, assignment_id=assignment["id"])
    assert document["owner_id"] == seed["ms"]
    assert len(client.get("/api/v1/assignments").json()["items"]) == 1
    client.cookies.clear()
    login(client, "teacher", seed["a"])
    assert client.get("/api/v1/documents/" + document["id"]).status_code == 200
    behalf = upload(client, assignment_id=assignment["id"], owner_id=seed["ms"])
    assert behalf["owner_id"] == seed["ms"]
    assert client.get(f"/api/v1/courses/{course['id']}/students").json()["items"][0]["enrolled"]


def test_cancel_purge_and_original_unavailable_after_deletion(client, seed):
    login(client, tenant=seed["a"])
    document = upload(client)
    assert client.post(f"/api/v1/documents/{document['id']}/cancel", json={}).status_code == 200
    assert not process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["state"] == "cancelled"
    assert client.delete("/api/v1/documents/" + document["id"]).status_code == 204
    assert client.get(f"/api/v1/documents/{document['id']}/original").status_code == 404
    assert process_next()
    assert not object_path(seed["a"], document["version_id"]).exists()


def test_expired_worker_lease_recovers_persisted_job(client, seed):
    login(client, tenant=seed["a"])
    document = upload(client)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT * FROM public.claim_document_job('lost-worker')")).first()
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.begin() as conn:
        conn.execute(
            text("UPDATE document_jobs SET lease_until=:expiry WHERE version_id=:id"),
            {"expiry": now() - timedelta(minutes=1), "id": document["version_id"]},
        )
    owner.dispose()
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["state"] == "completed"
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        job = db.scalar(select(DocumentJob))
        assert job.attempts == 2 and job.lease_token != "lost-worker"


def test_parser_syscalls_really_block_network_and_process_creation():
    code = """from app.documents.sandbox import restrict
import socket, os, json
restrict()
blocked=[]
for action in [lambda: socket.socket(), lambda: os.fork()]:
    try: action(); blocked.append(False)
    except PermissionError: blocked.append(True)
print(json.dumps(blocked))
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[true, true]"


def test_integrity_hash_prevents_processing_changed_original(client, seed):
    login(client, tenant=seed["a"])
    document = upload(client)
    path = object_path(seed["a"], document["version_id"])
    path.chmod(0o600)
    path.write_bytes(b"changed outside the product API")
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["error_code"] == "integrity_error"


def test_cancel_during_extraction_discards_real_result(client, seed, monkeypatch):
    from app.documents import jobs

    login(client, tenant=seed["a"])
    document = upload(client)
    original = jobs.run_extractor

    def extract_then_cancel(path, format):
        result = original(path, format)
        assert client.post(f"/api/v1/documents/{document['id']}/cancel", json={}).status_code == 200
        return result

    monkeypatch.setattr(jobs, "run_extractor", extract_then_cancel)
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["state"] == "cancelled"
    assert client.get(f"/api/v1/documents/{document['id']}/fragments").json()["items"] == []


def test_docx_resource_limit_rejects_excess_archive_entries(client, seed, monkeypatch):
    login(client, tenant=seed["a"])
    monkeypatch.setattr(settings(), "max_zip_entries", 3)
    document = upload(client, "many.docx", docx_bytes())
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["error_code"] == "unsafe_docx"


def test_expired_old_worker_cannot_overwrite_new_claim(client, seed, monkeypatch):
    from app.documents import jobs

    login(client, tenant=seed["a"])
    document = upload(client)
    original = jobs.run_extractor
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])

    def expire():
        with owner.begin() as conn:
            conn.execute(
                text("UPDATE document_jobs SET lease_until=:expiry WHERE version_id=:id"),
                {"expiry": now() - timedelta(minutes=1), "id": document["version_id"]},
            )

    def extract_then_reassign(path, format):
        result = original(path, format)
        expire()
        with engine.begin() as conn:
            assert conn.execute(text("SELECT * FROM public.claim_document_job('replacement-worker')")).first()
        return result

    monkeypatch.setattr(jobs, "run_extractor", extract_then_reassign)
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["state"] == "extracting"
    with Session(engine) as db, db.begin():
        context(db, institution_id=seed["a"])
        assert db.scalar(select(DocumentJob)).lease_token == "replacement-worker"
    monkeypatch.setattr(jobs, "run_extractor", original)
    expire()
    assert process_next()
    assert client.get("/api/v1/documents/" + document["id"]).json()["state"] == "completed"
    owner.dispose()


def test_database_commit_failure_removes_uncommitted_original(client, seed):
    from sqlalchemy import event

    login(client, tenant=seed["a"])

    def fail_outer_commit(session):
        if not session.in_nested_transaction() and session.info.get("uncommitted_files"):
            raise RuntimeError("intentional test transaction failure")

    event.listen(Session, "before_commit", fail_outer_commit)
    try:
        response = client.post("/api/v1/documents", files={"files": ("rollback.txt", b"valid document")})
        assert response.status_code == 500
    finally:
        event.remove(Session, "before_commit", fail_outer_commit)
    assert not list(Path(settings().storage_root).rglob("*.bin"))
    assert client.get("/api/v1/documents").json()["items"] == []


def test_document_migration_round_trip_preserves_identity_schema():
    assert os.environ["ENVIRONMENT"] == "test"
    assert "/aid_test" in os.environ["MIGRATION_DATABASE_URL"]
    owner = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with owner.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM users")).scalar_one()
    for target in ["0001_identity", "head"]:
        command = "downgrade" if target == "0001_identity" else "upgrade"
        result = subprocess.run(
            [sys.executable, "-m", "alembic", command, target], capture_output=True, text=True, timeout=20
        )
        assert result.returncode == 0, result.stderr
    with owner.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == before
        assert conn.execute(
            text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='documents'")
        ).one() == (True, True)
    owner.dispose()
