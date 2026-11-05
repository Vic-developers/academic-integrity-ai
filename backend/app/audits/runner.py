import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_engine(payload: dict) -> dict:
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    with tempfile.TemporaryDirectory(prefix="literal-audit-") as directory:
        input_path, output_path = Path(directory) / "input.json", Path(directory) / "result.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False))
        try:
            with output_path.open("wb") as stream:
                process = subprocess.run(
                    [sys.executable, "-m", "app.audits.run_child", str(input_path)],
                    env=environment,
                    cwd=directory,
                    stdout=stream,
                    stderr=subprocess.DEVNULL,
                    timeout=40,
                    close_fds=True,
                    start_new_session=True,
                )
            if process.returncode != 0:
                raise RuntimeError("engine_resource_limit")
            result = json.loads(output_path.read_text())
            if not result.get("ok"):
                raise RuntimeError(result.get("error", "engine_failed"))
            return result
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("engine_timeout") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("engine_failed") from exc
