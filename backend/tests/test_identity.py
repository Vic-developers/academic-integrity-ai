import os
import re
from datetime import timedelta
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
import pytest
from app.db import context, engine
from app.models import LoginSession, ResetToken
from app.security import digest, now
from app.worker import deliver
from conftest import PASSWORD, login


def test_login_selection_logout_and_rotation(client, seed):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": "wrong"}).status_code == 401
    )
    login(client)
    before = client.cookies["aid_session"]
    data = client.get("/api/v1/auth/me").json()
    assert len(data["memberships"]) == 1
    assert data["memberships"][0]["institution_id"] == seed["a"]
    assert client.get("/api/v1/users").status_code == 403
    assert client.post("/api/v1/auth/institution", json={"institution_id": seed["b"]}).status_code == 403
    assert client.post("/api/v1/auth/institution", json={"institution_id": seed["a"]}).status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies["aid_csrf"]
    assert client.cookies["aid_session"] != before
    assert client.get("/api/v1/statistics").json()["active_members"] == 3
    assert client.post("/api/v1/auth/logout", json={}).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_and_origin(client, seed):
    login(client, tenant=seed["a"])
    assert client.post("/api/v1/auth/logout", json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert (
        client.post("/api/v1/auth/logout", json={}, headers={"Origin": "https://attacker.invalid"}).status_code == 403
    )
    assert client.post("/api/v1/auth/logout", json={}, headers={"X-Requested-With": ""}).status_code == 403
    response = client.get("/api/v1/auth/me")
    assert response.headers["Cache-Control"] == "no-store"
    assert "password_hash" not in response.text


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_non_admin_cannot_manage_or_escalate(client, seed, role):
    login(client, role, seed["a"])
    assert client.get("/api/v1/users").status_code == 403
    assert (
        client.post(
            "/api/v1/users",
            json={"name": "Escalation", "email": "evil@example.org", "password": PASSWORD, "role": "admin"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/activity").status_code == 403


def test_admin_creates_only_in_selected_tenant(client, seed):
    login(client, tenant=seed["a"])
    body = {"name": "Nuevo", "email": "new@example.org", "password": PASSWORD, "role": "teacher"}
    assert client.post("/api/v1/users", json=body).status_code == 201
    rows = client.get("/api/v1/users").json()["items"]
    assert len(rows) == 4 and all(r["email"] != "outsider@example.org" for r in rows)
    assert (
        client.post("/api/v1/users", json={**body, "email": "super@example.org", "role": "superadmin"}).status_code
        == 403
    )
    actions = client.get("/api/v1/activity").json()["items"]
    assert all(a["action"] != "tenant.b.only" for a in actions)


def test_database_rls_and_pool_context(seed):
    with engine.begin() as conn:
        role = conn.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
        assert role == (False, False)
        assert conn.execute(text("SELECT count(*) FROM activity")).scalar_one() == 0
    with Session(engine) as db, db.begin():
        context(db, user_id=seed["admin"], institution_id=seed["a"])
        assert db.execute(text("SELECT action FROM activity")).scalars().all() == ["tenant.a.only"]
        assert db.execute(text("SELECT name FROM institutions")).scalars().all() == ["Universidad A"]
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM activity")).scalar_one() == 0
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.institution_id', :a, true)"), {"a": seed["a"]})
        conn.execute(
            text("INSERT INTO activity (id,institution_id,actor_id,action) VALUES ('invalid',:b,:actor,'leak')"),
            {"b": seed["b"], "actor": seed["mb"]},
        )
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.institution_id', :a, true)"), {"a": seed["a"]})
        conn.execute(
            text("INSERT INTO activity (id,institution_id,actor_id,action) VALUES ('bad-fk',:a,:actor,'invalid')"),
            {"a": seed["a"], "actor": seed["mb"]},
        )


def test_rate_limit_generic_errors_and_validation(client):
    for _ in range(10):
        assert (
            client.post("/api/v1/auth/login", json={"email": "missing@example.org", "password": "wrong"}).status_code
            == 401
        )
    assert (
        client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": PASSWORD}).status_code == 429
    )
    r = client.post("/api/v1/auth/login", json={"email": "bad", "password": "secret-value"})
    assert r.status_code == 422 and "secret-value" not in r.text
    assert r.headers["content-type"].startswith("application/problem+json")


def test_expired_session(client, seed):
    login(client, tenant=seed["a"])
    with Session(engine) as db, db.begin():
        session = db.get(LoginSession, digest(client.cookies["aid_session"]))
        session.expires_at = now() - timedelta(seconds=1)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_reset_through_real_smtp_single_use_and_session_revocation(client, seed):
    login(client, tenant=seed["a"])
    old_session = client.cookies["aid_session"]
    expected = client.post("/api/v1/auth/password-reset/request", json={"email": "admin@example.org"})
    absent = client.post("/api/v1/auth/password-reset/request", json={"email": "missing@example.org"})
    assert expected.status_code == absent.status_code == 202 and expected.json() == absent.json()
    assert deliver() == 1
    mail_url = os.environ["MAILPIT_URL"]
    with httpx.Client(trust_env=False) as http:
        messages = http.get(mail_url + "/api/v1/messages").json()["messages"]
        mail = next(m for m in messages if m["To"][0]["Address"] == "admin@example.org")
        message = http.get(mail_url + "/api/v1/message/" + mail["ID"]).json()
    token = re.search(r"token=([A-Za-z0-9_-]+)", message["Text"]).group(1)
    with Session(engine) as db:
        assert db.get(ResetToken, digest(token)) is not None
        assert db.get(ResetToken, token) is None
    body = {"token": token, "password": "New-test-password-2026!"}
    assert client.post("/api/v1/auth/password-reset/confirm", json=body).status_code == 200
    assert client.post("/api/v1/auth/password-reset/confirm", json=body).status_code == 400
    assert client.get("/api/v1/auth/me").status_code == 401
    with Session(engine) as db:
        assert db.get(LoginSession, digest(old_session)) is None
    assert (
        client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": PASSWORD}).status_code == 401
    )
    assert (
        client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": body["password"]}).status_code
        == 200
    )


def test_readiness_and_openapi(client):
    assert client.get("/api/health/ready").status_code == 200
    doc = client.get("/api/openapi.json").json()
    assert "/api/v1/auth/login" in doc["paths"]


@pytest.mark.parametrize(
    "role,users_status,activity_status",
    [
        ("superadmin", 200, 200),
        ("admin", 200, 200),
        ("coordinator", 200, 200),
        ("teacher", 403, 403),
        ("auditor", 403, 200),
        ("student", 403, 403),
    ],
)
def test_all_six_roles(client, seed, role, users_status, activity_status):
    admin_engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with admin_engine.begin() as conn:
        conn.execute(text("UPDATE memberships SET role=:role WHERE id=:id"), {"role": role, "id": seed["mt"]})
    admin_engine.dispose()
    login(client, "teacher", seed["a"])
    assert client.get("/api/v1/users").status_code == users_status
    assert client.get("/api/v1/activity").status_code == activity_status


def test_inactive_membership_revoked_immediately(client, seed):
    login(client, tenant=seed["a"])
    admin_engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with admin_engine.begin() as conn:
        conn.execute(text("UPDATE memberships SET active=false WHERE id=:id"), {"id": seed["ma"]})
    admin_engine.dispose()
    assert client.get("/api/v1/statistics").status_code == 403


def test_unavailable_rate_limiter_fails_closed(client):
    from app.config import settings

    cfg = settings()
    previous = cfg.redis_url
    try:
        cfg.redis_url = "redis://127.0.0.1:1/0"
        response = client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": PASSWORD})
        assert response.status_code == 503
    finally:
        cfg.redis_url = previous


def test_reset_expired_token_and_cookie_flags(client, seed):
    from app.config import settings

    cfg = settings()
    previous = cfg.secure_cookies
    cfg.secure_cookies = True
    try:
        response = client.post("/api/v1/auth/login", json={"email": "admin@example.org", "password": PASSWORD})
        cookies = response.headers.get_list("set-cookie")
        assert all("Secure" in c and "SameSite=lax" in c for c in cookies)
        assert "HttpOnly" in next(c for c in cookies if c.startswith("aid_session="))
    finally:
        cfg.secure_cookies = previous
    with Session(engine) as db, db.begin():
        db.add(ResetToken(id=digest("x" * 43), user_id=seed["admin"], expires_at=now() - timedelta(seconds=1)))
    assert (
        client.post("/api/v1/auth/password-reset/confirm", json={"token": "x" * 43, "password": PASSWORD}).status_code
        == 400
    )


def test_concurrent_reset_token_can_only_be_used_once(seed):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from app.main import app

    token = "concurrent-reset-token-for-testing-only-2026"
    with Session(engine) as db, db.begin():
        db.add(ResetToken(id=digest(token), user_id=seed["admin"], expires_at=now() + timedelta(minutes=5)))

    def reset():
        with TestClient(
            app, headers={"Origin": "http://localhost:5173", "X-Requested-With": "AcademicIntegrityAI"}
        ) as client:
            return client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": token, "password": "Concurrent-new-password-2026!"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reset(), range(2)))
    assert sorted(results) == [200, 400]


@pytest.mark.parametrize("role", ["admin", "superadmin"])
def test_cli_provisions_real_admin_and_login(client, monkeypatch, role):
    from app import cli

    owner_engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    monkeypatch.setattr(cli, "engine", owner_engine)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli",
            "--institution",
            "Institución CLI",
            "--email",
            "cli@example.org",
            "--name",
            "Admin CLI",
            "--role",
            role,
        ],
    )
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: PASSWORD)
    cli.main()
    owner_engine.dispose()
    response = client.post("/api/v1/auth/login", json={"email": "cli@example.org", "password": PASSWORD})
    assert response.status_code == 200
    profile = client.get("/api/v1/auth/me").json()
    assert profile["memberships"][0]["name"] == "Institución CLI"
    assert profile["memberships"][0]["role"] == role
