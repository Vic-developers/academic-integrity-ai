"""Generate local secrets once. Standard library only; compatible with Windows Python."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit("Ya existe .env; no se sobrescribe")
owner, app = secrets.token_hex(24), secrets.token_hex(24)
target.write_text(
    f"POSTGRES_PASSWORD={owner}\nAPP_DB_PASSWORD={app}\n"
    f"DATABASE_URL=postgresql+psycopg://aid_app:{app}@localhost:55432/academic_integrity\n"
    f"MIGRATION_DATABASE_URL=postgresql+psycopg://aid_owner:{owner}@localhost:55432/academic_integrity\n"
    "REDIS_URL=redis://localhost:56379/0\nPUBLIC_ORIGIN=http://localhost:5173\n"
    "ENVIRONMENT=development\nSECURE_COOKIES=false\nSMTP_HOST=localhost\nSMTP_PORT=51025\n",
    encoding="utf-8",
)
target.chmod(0o600)
print(".env creado con secretos aleatorios. No subirlo a Git.")
