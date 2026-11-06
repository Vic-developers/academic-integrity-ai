"""Offline CPU experiment. Explicit corpus input; never reads .env or institutional records."""

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.experimental_ai.corpus import canonical
from app.experimental_ai.training import train


def run(corpus_path, output, *, allow_technical_fixture=False):
    if corpus_path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("corpus_file_budget")

    def reject(value):
        raise ValueError("non_finite_json")

    data = json.loads(corpus_path.read_text(encoding="utf-8"), parse_constant=reject)
    if data.get("purpose") == "technical_fixture" and not allow_technical_fixture:
        raise ValueError("technical_fixture_not_allowed_for_requested_research_model")
    started = time.perf_counter()
    result = train(data)
    elapsed = time.perf_counter() - started
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = output / result["manifest"]["experiment_id"]
    if destination.exists():
        raise FileExistsError("Immutable experiment already exists")
    staging = Path(tempfile.mkdtemp(prefix=".experiment-", dir=output))
    try:
        for key in ["manifest", "model", "report"]:
            path = staging / (key + ".json")
            path.write_bytes(canonical(result[key]) + b"\n")
            path.chmod(0o600)
        (staging / "execution.json").write_bytes(
            canonical(
                {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "seconds": elapsed,
                    "cpu_only": True,
                    "samples": len(data["samples"]),
                    "approved": False,
                }
            )
            + b"\n"
        )
        (staging / "execution.json").chmod(0o600)
        # rename only after all data-only artifacts have been written privately.
        os.rename(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination, result["manifest"]["experiment_id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-technical-fixture",
        action="store_true",
        help="Only replay historical software tests; never an authorship research model",
    )
    args = parser.parse_args()
    try:
        path, identity = run(
            args.corpus,
            args.output,
            allow_technical_fixture=args.allow_technical_fixture,
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Error codes only: do not echo private corpus data or paths.
        print("Experiment rejected:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(2) from None
    print("Research experiment:", identity)
    print("Approved for document authorship assessment: false")
