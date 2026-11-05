"""Original-codepoint passages constrained by the actual tokenizer, without silent truncation."""

import re
from app.documents.normalization import sentences

CHUNKER_VERSION = "sentence-token-budget-v1"


def passages(original: str, token_count, max_tokens: int, *, min_words=8, overlap_words=16, max_passages=200):
    if max_tokens < 4 or min_words < 1 or overlap_words < 0 or max_passages < 1:
        raise ValueError("Invalid chunk budget")
    if len(original) > 100_000:
        raise ValueError("Passage input exceeds character budget")
    units = []
    skipped = []
    for sentence in sentences(original):
        a, b = sentence["start"], sentence["end"]
        if token_count(original[a:b]) <= max_tokens:
            units.append((a, b))
            continue
        words = list(re.finditer(r"\S+", original[a:b]))
        start = 0
        while start < len(words):
            end = start
            while (
                end < len(words)
                and token_count(original[a + words[start].start() : a + words[end].end()]) <= max_tokens
            ):
                end += 1
            if end == start:
                skipped.append(
                    {
                        "start": a + words[start].start(),
                        "end": a + words[start].end(),
                        "reason": "word_exceeds_token_budget",
                    }
                )
                start += 1
                continue
            units.append((a + words[start].start(), a + words[end - 1].end()))
            if end == len(words):
                break
            start = max(start + 1, end - min(overlap_words, max(0, (end - start) // 2)))
    groups = []
    active = None
    previous_unit = None
    for a, b in units:
        if active is not None and token_count(original[active[0] : b]) <= max_tokens:
            active = (active[0], b)
        else:
            if active is not None:
                groups.append(active)
            if previous_unit is not None and token_count(original[previous_unit[0] : b]) <= max_tokens:
                active = (previous_unit[0], b)
            else:
                active = (a, b)
        previous_unit = (a, b)
    if active is not None:
        groups.append(active)
    result = []
    for a, b in groups:
        words = len(re.findall(r"\w+", original[a:b]))
        if words < min_words:
            skipped.append({"start": a, "end": b, "reason": "passage_below_minimum_words"})
            continue
        if len(result) >= max_passages:
            skipped.append({"start": a, "end": b, "reason": "passage_budget"})
            continue
        count = token_count(original[a:b])
        if count > max_tokens:
            raise ValueError("Tokenizer budget contract violated")
        result.append({"start": a, "end": b, "text": original[a:b], "tokens": count, "words": words})
    return {
        "version": CHUNKER_VERSION,
        "offset_unit": "unicode_code_points",
        "passages": result,
        "skipped": skipped,
        "coverage": "partial" if skipped or not result else "complete_for_supplied_fragment",
    }
