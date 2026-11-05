"""Synthetic fixtures. Refuse to touch databases other than aid_test."""

import os
import shutil
import uuid
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.models import Activity, Institution, Membership, User
from app.security import hasher

PASSWORD = "Test-only-password-2026!"


def seed_test_data() -> dict[str, str]:
    # Refuse a database not explicitly labelled as disposable test infrastructure.
    if (
        os.environ.get("ENVIRONMENT") != "test"
        or os.environ.get("ALLOW_TEST_DATABASE_RESET") != "yes"
        or make_url(os.environ["DATABASE_URL"]).database != "aid_test"
        or not os.environ["REDIS_URL"].endswith("/15")
    ):
        raise RuntimeError("Use the isolated test stack and ALLOW_TEST_DATABASE_RESET=yes")
    storage = os.environ.get("STORAGE_ROOT", "")
    if storage == "/tmp/academic-integrity-aid_test-documents":
        shutil.rmtree(storage, ignore_errors=True)
    admin_engine = create_engine(os.environ["MIGRATION_DATABASE_URL"])
    with admin_engine.begin() as conn:
        conn.execute(
            text("TRUNCATE activity, email_jobs, reset_tokens, sessions, memberships, institutions, users CASCADE")
        )
    Redis.from_url(os.environ["REDIS_URL"]).flushdb()
    ids = {
        key: str(uuid.uuid4()) for key in ["a", "b", "admin", "teacher", "student", "outsider", "ma", "mt", "ms", "mb"]
    }
    with Session(admin_engine) as db, db.begin():
        db.add_all([Institution(id=ids["a"], name="Universidad A"), Institution(id=ids["b"], name="Universidad B")])
        db.add_all(
            [
                User(id=ids[key], email=key + "@example.org", name=key.title(), password_hash=hasher.hash(PASSWORD))
                for key in ["admin", "teacher", "student", "outsider"]
            ]
        )
        db.flush()
        for key, user, tenant, role in [
            ("ma", "admin", "a", "admin"),
            ("mt", "teacher", "a", "teacher"),
            ("ms", "student", "a", "student"),
            ("mb", "outsider", "b", "admin"),
        ]:
            db.add(Membership(id=ids[key], user_id=ids[user], institution_id=ids[tenant], role=role))
        db.flush()
        db.add_all(
            [
                Activity(institution_id=ids["a"], actor_id=ids["ma"], action="tenant.a.only"),
                Activity(institution_id=ids["b"], actor_id=ids["mb"], action="tenant.b.only"),
            ]
        )
    admin_engine.dispose()
    return ids


if __name__ == "__main__":
    seed_test_data()
    print("Fixtures preparadas exclusivamente en aid_test")
