"""Reproducible technical corpus. It is NOT an academic validation dataset."""

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

from app.audits.engine import ENGINE_VERSION, compare
from app.documents.normalization import NORMALIZER, fragment


def evaluate():
    rng = random.Random(20261105)
    cases = []
    for number in range(120):
        shared = [f"lexema{number}_{i}" for i in range(rng.randint(8, 64))]
        q = (
            ["entrada_q", "sección_q", "contexto_q", "propio_q"]
            + shared
            + ["cierre_q", "anexo_q"]
        )
        s = (
            ["entrada_s", "sección_s", "contexto_s", "ajeno_s"]
            + shared
            + ["cierre_s", "anexo_s"]
        )
        cases.append((" ".join(q), " ".join(s), set(range(4, 4 + len(shared)))))
    for number in range(80):
        cases.append(
            (
                " ".join(f"consulta{number}_{i}" for i in range(32)),
                " ".join(f"referencia{number}_{i}" for i in range(32)),
                set(),
            )
        )
    # Spanish words with case and Unicode-equivalent source spelling; independent word-index annotations.
    q = "introducción personal propia única árbol ss fi uno dos tres cuatro cinco seis siete ocho final objetivo"
    s = "referencia institucional ajena distinta ÁRBOL ß ﬁ uno dos tres cuatro cinco seis siete ocho cierre diferente"
    cases.append((q, s, set(range(4, 15))))
    tp = fp = fn = positive_hits = negative_hits = 0
    start = time.perf_counter()
    for target, source, expected in cases:
        result = compare(
            [{"id": "query", **fragment(target, 1)}],
            [
                {
                    "id": "source",
                    "fragments": [{"id": "reference", **fragment(source, 1)}],
                }
            ],
        )
        assert result["partial_reason"] is None
        actual = set()
        for found in result["findings"]:
            actual.update(range(found["target_start"], found["target_end"]))
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)
        if expected:
            positive_hits += bool(actual)
        else:
            negative_hits += bool(actual)
    elapsed = time.perf_counter() - start
    corpus_sha = hashlib.sha256(
        json.dumps(
            [(a, b, sorted(c)) for a, b, c in cases], ensure_ascii=False
        ).encode()
    ).hexdigest()
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {
        "protocol": "literal-technical-v1",
        "seed": 20261105,
        "engine_version": ENGINE_VERSION,
        "normalizer": NORMALIZER,
        "corpus_sha256": corpus_sha,
        "provenance": "Synthetic fixtures generated locally; no student documents or web sources",
        "cases": len(cases),
        "positives": 121,
        "negatives": 80,
        "word_positions": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
        },
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall)
        if precision + recall
        else 0,
        "positive_documents_retrieved": positive_hits,
        "negative_documents_flagged": negative_hits,
        "elapsed_seconds": elapsed,
        "acceptance": {
            "precision_at_least_0_98": precision >= 0.98,
            "recall_at_least_0_95": recall >= 0.95,
        },
        "limitations": [
            "Controlled technical corpus, not representative of academic writing",
            "No measurement of Internet source coverage",
            "No plagiarism or authorship classification",
            "No claim of production throughput",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = evaluate()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "cases",
                    "precision",
                    "recall",
                    "f1",
                    "positive_documents_retrieved",
                    "negative_documents_flagged",
                ]
            }
        )
    )
    assert all(result["acceptance"].values()), "Technical acceptance gate failed"
