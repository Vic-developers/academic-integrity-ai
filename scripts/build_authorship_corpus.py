"""Compile an explicitly authorized, real-text corpus. No generated placeholder samples."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.experimental_ai.corpus import canonical, validate


def build(collection_path, output):
    if collection_path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("collection_budget")
    source = json.loads(collection_path.read_text(encoding="utf-8"))
    if (
        source.get("purpose") != "research"
        or source.get("synthetic_patterns_allowed") is not False
    ):
        raise ValueError("real_research_only")
    catalog = source.get("source_catalog", {})
    if not isinstance(catalog, dict):
        raise TypeError("source_catalog")
    root = collection_path.resolve().parent
    rows = []
    total_characters = 0
    samples = source.get("samples", [])
    if not isinstance(samples, list) or not 8 <= len(samples) <= 2000:
        raise ValueError("sample_budget")
    for record in samples:
        rights = catalog.get(record.get("source_id"), {})
        if not all(
            rights.get(k) is True
            for k in ["training_allowed", "evaluation_allowed", "rights_reviewed"]
        ):
            raise ValueError("source_rights_missing")
        if rights.get("kind") not in {
            "published_human",
            "recorded_ai_generation",
            "curated_human_ai_dataset",
        }:
            raise ValueError("unqualified_source")
        if any(
            not isinstance(rights.get(k), str) or len(rights[k]) < 10
            for k in ["license_reference", "permission_reference", "label_provenance"]
        ):
            raise ValueError("source_evidence_missing")
        path = (root / record["text_path"]).resolve()
        if not path.is_relative_to(root) or path.suffix != ".txt":
            raise ValueError("text_path_outside_collection")
        if path.stat().st_size > 200000:
            raise ValueError("sample_file_budget")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("text_sha256"):
            raise ValueError("sample_file_hash_changed")
        row = {
            key: value
            for key, value in record.items()
            if key not in {"text_path", "text_sha256"}
        }
        row["text"] = data.decode("utf-8")
        total_characters += len(row["text"])
        if total_characters > 2_000_000 or len(row["text"]) > 50000:
            raise ValueError("corpus_text_budget")
        rows.append(row)
    corpus = {
        k: source[k]
        for k in [
            "dataset_id",
            "license",
            "authorization_reference",
            "annotation_protocol",
            "training_allowed",
            "evaluation_allowed",
            "personal_data_reviewed",
        ]
    }
    corpus.update(
        schema="experimental-authorship-corpus-v1",
        purpose="research",
        source_catalog=catalog,
        samples=rows,
    )
    manifest = validate(corpus)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(corpus) + b"\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.collection, args.output)
    except (ValueError, OSError, KeyError, TypeError):
        print(
            "Corpus rejected; check source rights, hashes and group separation.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    print("Qualified corpus SHA-256:", result["sha256"])
    print("Model trained or approved: false")
