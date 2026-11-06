"""Versioned observables. These measurements do not identify human or AI authorship."""

import hashlib
import math
import re
import unicodedata
from collections import Counter

VERSION = "linguistic-observations-v1"
FEATURES = (
    "mattr_50",
    "hapax_ratio",
    "repeated_trigram_ratio",
    "sentence_length_cv",
    "mean_sentence_tokens",
    "mean_word_characters",
    "punctuation_per_token",
    "paragraphs_per_100_tokens",
)
TOKEN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def tokens(text):
    return TOKEN.findall(unicodedata.normalize("NFKC", text).casefold())


def measure(text):
    if len(text) > 500_000:
        raise ValueError("linguistic_text_budget")
    words = tokens(text)
    n = len(words)
    counts = Counter(words)
    window = min(50, n)
    moving = Counter(words[:window])
    total = len(moving) / window if window else 0.0
    windows = 1 if window else 0
    for end in range(window, n):
        leaving = words[end - window]
        moving[leaving] -= 1
        if not moving[leaving]:
            del moving[leaving]
        moving[words[end]] += 1
        total += len(moving) / window
        windows += 1
    triples = Counter(tuple(words[i : i + 3]) for i in range(max(0, n - 2)))
    repeated = sum(c - 1 for c in triples.values())
    # Decimal punctuation stays inside a sentence; no syntactic parser is claimed.
    sentences = [
        len(tokens(part)) for part in re.split(r"(?<!\d)[.!?]+(?:\s+|$)|(?<=\d)[.!?]+(?!\d)(?:\s+|$)|\n+", text)
    ]
    lengths = [v for v in sentences if v]
    mean = sum(lengths) / len(lengths) if lengths else 0.0
    cv = math.sqrt(sum((x - mean) ** 2 for x in lengths) / len(lengths)) / mean if mean else 0.0
    paragraphs = sum(bool(p.strip()) for p in re.split(r"\n\s*\n", text))
    values = {
        "mattr_50": total / windows if windows else 0.0,
        "hapax_ratio": sum(v == 1 for v in counts.values()) / n if n else 0.0,
        "repeated_trigram_ratio": repeated / max(1, n - 2),
        "sentence_length_cv": cv,
        "mean_sentence_tokens": mean,
        "mean_word_characters": sum(map(len, words)) / n if n else 0.0,
        "punctuation_per_token": sum(unicodedata.category(c).startswith("P") for c in text) / n if n else 0.0,
        "paragraphs_per_100_tokens": 100 * paragraphs / n if n else 0.0,
    }
    return {
        "engine": VERSION,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "counts": {
            "unicode_code_points": len(text),
            "tokens": n,
            "distinct_tokens": len(counts),
            "sentences": len(lengths),
            "paragraphs": paragraphs,
            "trigrams": max(0, n - 2),
            "repeated_trigram_occurrences": repeated,
            "mattr_window": window,
            "mattr_windows": windows,
        },
        "values": values,
        "assessment": "not_conclusive",
        "authorship_probability": None,
        "abstention_reasons": ["no_approved_calibrated_authorship_model"]
        + (["text_below_100_tokens"] if n < 100 else []),
        "limitations": [
            "observed_text_statistics_do_not_establish_authorship",
            "tokenization_is_not_syntactic_or_semantic_analysis",
            "extraction_layout_and_text_length_affect_measurements",
        ],
    }
