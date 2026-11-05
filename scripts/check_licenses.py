"""Capture installed runtime metadata. Exact notices still require review before distribution."""

import argparse
import json
import re
from importlib import metadata
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = []
for line in (root / "backend/requirements.lock").read_text().splitlines():
    match = re.match(r"([\w.-]+)(?:\[[^]]+\])?==([^\s\\]+)", line)
    if not match:
        continue
    name, version = match.groups()
    distribution = metadata.distribution(name)
    info = distribution.metadata
    license_value = (
        info.get("License-Expression")
        or info.get("License")
        or "; ".join(
            c for c in info.get_all("Classifier", []) if c.startswith("License ::")
        )
    )
    rows.append(
        {
            "name": name,
            "version": version,
            "license_declared": license_value,
            "installed_version": distribution.version,
            "license_files": [
                str(f)
                for f in distribution.files or []
                if "license" in str(f).lower() or "copying" in str(f).lower()
            ],
        }
    )
assert all(r["installed_version"] == r["version"] for r in rows)
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default=str(root / "docs/validation"))
output = Path(parser.parse_args().output_dir) / "runtime-licenses.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
print(f"{len(rows)} distribuciones registradas")
