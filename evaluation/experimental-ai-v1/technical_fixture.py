"""Invented pattern labels for pipeline checks ONLY; not human/AI research data."""

import json
import sys
from pathlib import Path


def corpus():
    rows = []
    for split in ["train", "validation", "calibration", "test"]:
        for label in ["human", "ai"]:
            for i in range(6):
                identity = f"{split}-{label}-{i}"
                if label == "human":
                    words = [f"{identity}termino{k}" for k in range(60 + i * 3)]
                    # Hyphens tokenize separately; identity words deliberately differ across splits.
                    text = " ".join(words[:17]) + ". " + " ".join(words[17:]) + "."
                else:
                    base = [f"{split}{i}patron{k}" for k in range(5)]
                    text = (". ".join([" ".join(base)] * (12 + i))) + "."
                rows.append(
                    {
                        "id": identity,
                        "document_id": identity,
                        "author_id": identity,
                        "source_id": identity,
                        "prompt_id": identity,
                        "language": "es",
                        "domain": "technical-fixture",
                        "generator": "invented-patterns-not-authorship-ground-truth",
                        "provenance_reference": "technical-fixture-created-for-project-tests",
                        "label": label,
                        "split": split,
                        "text": text,
                    }
                )
    return {
        "schema": "experimental-authorship-corpus-v1",
        "dataset_id": "technical-pattern-fixture-v1",
        "purpose": "technical_fixture",
        "license": "CC0-1.0 (invented test patterns only)",
        "authorization_reference": "Project-generated technical strings; no institutional documents",
        "annotation_protocol": "Arbitrary binary pattern labels exercise code; neither label asserts real authorship",
        "training_allowed": True,
        "evaluation_allowed": True,
        "personal_data_reviewed": True,
        "samples": rows,
    }


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    destination.write_text(json.dumps(corpus(), ensure_ascii=False), encoding="utf-8")
    destination.chmod(0o600)
    print("Technical fixture written; not scientific authorship data")
