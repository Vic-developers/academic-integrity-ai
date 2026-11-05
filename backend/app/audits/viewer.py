"""Read the immutable fragment behind evidence; never guess PDF glyph positions."""

import hashlib
import math
from fastapi import HTTPException


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verified_range(fragment, span: dict) -> tuple[int, int]:
    a, b = span["original_start"], span["original_end"]
    if (
        not (0 <= a < b <= len(fragment.original))
        or digest(fragment.original) != span["fragment_sha256"]
        or digest(fragment.original[a:b]) != span["span_sha256"]
    ):
        raise HTTPException(409, "La evidencia no coincide con su versión documental")
    return a, b


def boxes(original: str, locations: list, start: int, end: int) -> list[list[float]] | None:
    covered = set()
    result = []
    for loc in locations:
        if loc.get("kind") != "pdf_word" or loc.get("end", 0) <= start or loc.get("start", len(original)) >= end:
            continue
        chars = loc.get("chars", [])
        if (
            not loc.get("char_mapping_reliable")
            or "".join(c["text"] for c in chars) != original[loc["start"] : loc["end"]]
        ):
            return None
        offset = loc["start"]
        for char in chars:
            stop = offset + len(char["text"])
            if offset < end and stop > start:
                # A glyph spanning multiple codepoints may only be highlighted as a whole.
                if offset < start or stop > end:
                    return None
                box = char.get("bbox", [])
                if (
                    len(box) != 4
                    or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in box)
                    or box[2] <= box[0]
                    or box[3] <= box[1]
                ):
                    return None
                result.append(box)
                covered.update(range(offset, stop))
            offset = stop
    expected = {i for i in range(start, end) if not original[i].isspace()}
    return result if expected <= covered and result else None
