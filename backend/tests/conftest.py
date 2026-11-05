"""Integration tests require the dedicated disposable PostgreSQL/Redis stack."""

import pytest
from fastapi.testclient import TestClient
from app.db import engine
from app.main import app
from seed import PASSWORD, seed_test_data


@pytest.fixture(autouse=True)
def seed():
    yield seed_test_data()
    engine.dispose()


@pytest.fixture
def client():
    with TestClient(
        app, headers={"Origin": "http://localhost:5173", "X-Requested-With": "AcademicIntegrityAI"}
    ) as client:
        yield client


def login(client, user="admin", tenant=None):
    result = client.post("/api/v1/auth/login", json={"email": user + "@example.org", "password": PASSWORD})
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = client.cookies["aid_csrf"]
    if tenant:
        result = client.post("/api/v1/auth/institution", json={"institution_id": tenant})
        assert result.status_code == 200, result.text
        client.headers["X-CSRF-Token"] = client.cookies["aid_csrf"]
