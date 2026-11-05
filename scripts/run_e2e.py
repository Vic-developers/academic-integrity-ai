"""Run browser tests against dedicated aid_test; restore normal services on exit."""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
env = dotenv_values(root / ".env")
url = (
    "postgresql+psycopg://aid_app:" + str(env["APP_DB_PASSWORD"]) + "@db:5432/aid_test"
)
config = {
    "services": {
        s: {
            "environment": {
                "DATABASE_URL": url,
                "ENVIRONMENT": "test",
                "REDIS_URL": "redis://redis:6379/15",
            }
        }
        for s in ["api", "worker"]
    }
}
test_env = {**os.environ, **{k: v for k, v in env.items() if v is not None}}
test_env.update(
    DATABASE_URL=make_url(str(env["DATABASE_URL"]))
    .set(database="aid_test")
    .render_as_string(hide_password=False),
    MIGRATION_DATABASE_URL=make_url(str(env["MIGRATION_DATABASE_URL"]))
    .set(database="aid_test")
    .render_as_string(hide_password=False),
    REDIS_URL=str(env["REDIS_URL"]).rsplit("/", 1)[0] + "/15",
    ENVIRONMENT="test",
    ALLOW_TEST_DATABASE_RESET="yes",
    PYTHONPATH=str(root / "backend"),
)
subprocess.run(
    [sys.executable, "tests/seed.py"], cwd=root / "backend", env=test_env, check=True
)
with tempfile.TemporaryDirectory(prefix="academic-integrity-e2e-") as tmp:
    override = Path(tmp) / "test.yaml"
    override.write_text(json.dumps(config))
    override.chmod(0o600)
    base = ["docker", "compose", "-f", str(root / "compose.yaml")]
    try:
        subprocess.run(
            base
            + [
                "-f",
                str(override),
                "up",
                "-d",
                "--force-recreate",
                "--no-deps",
                "--no-build",
                "api",
                "worker",
                "frontend",
            ],
            check=True,
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for attempt in range(30):
            try:
                with opener.open(
                    "http://localhost:5173/api/health/ready", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                if attempt == 29:
                    raise RuntimeError("El stack no llegó a estar disponible") from None
                time.sleep(1)
        subprocess.run(
            ["npm", "run", "test:e2e"],
            cwd=root / "frontend",
            env=os.environ.copy(),
            check=True,
        )
    finally:
        subprocess.run(
            base
            + [
                "up",
                "-d",
                "--force-recreate",
                "--no-deps",
                "--no-build",
                "api",
                "worker",
                "frontend",
            ],
            check=True,
        )
