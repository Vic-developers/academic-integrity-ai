import os
import uuid
from pathlib import Path
from app.config import settings


def object_path(tenant: str, version: str) -> Path:
    # No client filenames or paths participate in storage keys.
    tenant, version = str(uuid.UUID(tenant)), str(uuid.UUID(version))
    root = Path(settings().storage_root).resolve()
    folder = root / tenant
    if folder.is_symlink():
        raise ValueError("Invalid storage directory")
    return folder / (version + ".bin")


def write_original(tenant: str, version: str, source) -> Path:
    path = object_path(tenant, version)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    created = False
    try:
        with path.open("xb") as target:
            created = True
            os.chmod(path, 0o600)
            source.seek(0)
            while chunk := source.read(65536):
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(path, 0o400)
        return path
    except BaseException:
        if created:
            path.unlink(missing_ok=True)
        raise
