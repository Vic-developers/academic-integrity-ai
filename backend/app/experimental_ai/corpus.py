"""Explicitly authorized offline corpus; no institutional database or downloads."""

import hashlib
import json
from collections import Counter
from app.experimental_ai.features import tokens

SPLITS = ("train", "validation", "calibration", "test")
LABELS = {"human", "ai", "mixed", "edited"}


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def fingerprint(text):
    return hashlib.sha256(" ".join(tokens(text)).encode()).hexdigest()


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != "experimental-authorship-corpus-v1":
        raise ValueError("corpus_schema")
    for key in ["dataset_id", "license", "authorization_reference", "annotation_protocol"]:
        if not isinstance(data.get(key), str) or not 3 <= len(data[key]) <= 500:
            raise ValueError("corpus_provenance")
    if (
        data.get("training_allowed") is not True
        or data.get("evaluation_allowed") is not True
        or data.get("personal_data_reviewed") is not True
    ):
        raise ValueError("corpus_authorization")
    if data.get("purpose") not in {"research", "technical_fixture"}:
        raise ValueError("corpus_purpose")
    rows = data.get("samples")
    if not isinstance(rows, list) or not 8 <= len(rows) <= 2000:
        raise ValueError("corpus_sample_budget")
    seen_ids = set()
    groups = {}
    hashes = {}
    shingles = {}
    total = 0
    counts = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("corpus_sample")
        for key in [
            "id",
            "document_id",
            "author_id",
            "source_id",
            "prompt_id",
            "language",
            "domain",
            "generator",
            "provenance_reference",
        ]:
            if not isinstance(row.get(key), str) or not 1 <= len(row[key]) <= 500:
                raise ValueError("sample_provenance")
        if row["id"] in seen_ids:
            raise ValueError("duplicate_sample_id")
        seen_ids.add(row["id"])
        split = row.get("split")
        label = row.get("label")
        text = row.get("text")
        if split not in SPLITS or label not in LABELS:
            raise ValueError("sample_split_or_label")
        if not isinstance(text, str) or not 20 <= len(text) <= 50000:
            raise ValueError("sample_text_budget")
        total += len(text)
        if total > 2_000_000:
            raise ValueError("corpus_text_budget")
        word_list = tokens(text)
        if len(word_list) < 10:
            raise ValueError("sample_too_short")
        for key in ["document_id", "author_id", "source_id", "prompt_id"]:
            identity = (key, row[key])
            if identity in groups and groups[identity] != split:
                raise ValueError("cross_split_group_leakage")
            groups[identity] = split
        text_hash = fingerprint(text)
        if text_hash in hashes:
            raise ValueError("duplicate_normalized_text")
        hashes[text_hash] = split
        # Conservative shared eight-token spans flag near duplicates/templates across splits.
        for i in range(len(word_list) - 7):
            item = hashlib.sha256(" ".join(word_list[i : i + 8]).encode()).digest()
            if item in shingles and shingles[item] != split:
                raise ValueError("cross_split_shared_eight_tokens")
            shingles[item] = split
        counts[split, label] += 1
        if split in {"train", "calibration"} and label not in {"human", "ai"}:
            raise ValueError("nonbinary_training_or_calibration_label")
    for split in SPLITS:
        for label in ["human", "ai"]:
            if counts[split, label] < 2:
                raise ValueError("insufficient_binary_split")
    return {
        "dataset_id": data["dataset_id"],
        "sha256": hashlib.sha256(canonical(data)).hexdigest(),
        "purpose": data["purpose"],
        "license": data["license"],
        "authorization_reference": data["authorization_reference"],
        "annotation_protocol": data["annotation_protocol"],
        "counts": {split: {label: counts[split, label] for label in sorted(LABELS)} for split in SPLITS},
        "split_checks": [
            "document_author_source_prompt_disjoint",
            "normalized_text_unique",
            "no_cross_split_shared_eight_tokens",
        ],
        "authorization_is_attested_not_independently_verified": True,
    }
