"""Run only against a separate aid_test database on the development PostgreSQL instance."""

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env")
owner = make_url(os.environ["MIGRATION_DATABASE_URL"])
app = make_url(os.environ["DATABASE_URL"])
with psycopg.connect(
    owner.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    ),
    autocommit=True,
) as conn:
    if not conn.execute(
        "SELECT 1 FROM pg_database WHERE datname='aid_test'"
    ).fetchone():
        conn.execute("CREATE DATABASE aid_test")
os.environ.update(
    DATABASE_URL=app.set(database="aid_test").render_as_string(hide_password=False),
    MIGRATION_DATABASE_URL=owner.set(database="aid_test").render_as_string(
        hide_password=False
    ),
    REDIS_URL=os.environ["REDIS_URL"].rsplit("/", 1)[0] + "/15",
    ENVIRONMENT="test",
    ALLOW_TEST_DATABASE_RESET="yes",
    MAILPIT_URL=os.environ.get("MAILPIT_URL", "http://localhost:8025"),
)
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=root / "backend",
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
    cwd=root / "backend",
    check=True,
)
