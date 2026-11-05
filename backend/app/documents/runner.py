import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from app.config import settings
from app.documents.validation import DocumentError


def run_extractor(path: Path, format: str) -> dict:
    cfg = settings()
    # No session, DB credentials, SMTP passwords, cloud tokens or inherited proxy credentials.
    environment = {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        "DATABASE_URL": "postgresql+psycopg://unused",
        "ENVIRONMENT": "test",
        "MAX_PDF_PAGES": str(cfg.max_pdf_pages),
        "MAX_ZIP_BYTES": str(cfg.max_zip_bytes),
        "MAX_ZIP_ENTRIES": str(cfg.max_zip_entries),
        "MAX_DOCUMENT_CHARS": str(cfg.max_document_chars),
    }
    with tempfile.TemporaryDirectory(prefix="ai-extract-") as directory:
        output = Path(directory) / "result.json"
        try:
            with output.open("wb") as stream:
                completed = subprocess.run(
                    [sys.executable, "-m", "app.documents.extractor", str(path.resolve()), format],
                    cwd=directory,
                    env=environment,
                    stdout=stream,
                    stderr=subprocess.DEVNULL,
                    timeout=cfg.extraction_timeout,
                    close_fds=True,
                    start_new_session=True,
                )
            if completed.returncode != 0 or output.stat().st_size > 32 * 1024 * 1024:
                raise DocumentError("extraction_timeout")
            result = json.loads(output.read_text())
            if not result.get("ok"):
                raise DocumentError(result.get("error", "extraction_failed"))
            return result
        except subprocess.TimeoutExpired as exc:
            raise DocumentError("extraction_timeout") from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise DocumentError("extraction_failed") from exc
