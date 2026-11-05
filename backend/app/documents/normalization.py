import re
import unicodedata

NORMALIZER = "nfkc-casefold-map-v1"


def normalize(original: str) -> tuple[str, list[list[int]]]:
    output: list[str] = []
    mapping: list[list[int]] = []
    # Combining sequences remain together so e + acute maps to the complete original span.
    clusters: list[tuple[int, int]] = []
    for index, char in enumerate(original):
        if clusters and unicodedata.category(char).startswith("M"):
            clusters[-1] = (clusters[-1][0], index + 1)
        else:
            clusters.append((index, index + 1))
    for start, end in clusters:
        for char in unicodedata.normalize("NFKC", original[start:end]).casefold():
            if unicodedata.category(char) == "Cf":
                continue
            if char.isspace():
                if not output:
                    continue
                if output[-1] == " ":
                    mapping[-1][1] = end
                    continue
                char = " "
            output.append(char)
            mapping.append([start, end])
    if output and output[-1] == " ":
        output.pop()
        mapping.pop()
    return "".join(output), mapping


def sentences(original: str) -> list[dict]:
    ranges = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", original):
        start = match.start()
        while start < match.end() and original[start].isspace():
            start += 1
        if start < match.end():
            ranges.append({"start": start, "end": match.end()})
    return ranges


def fragment(
    original: str, paragraph: int, *, page: int | None = None, locations: list | None = None, section: str | None = None
) -> dict:
    normalized, mapping = normalize(original)
    return {
        "original": original,
        "normalized": normalized,
        "mapping": mapping,
        "paragraph": paragraph,
        "page": page,
        "locations": locations or [],
        "sentences": sentences(original),
        "section": section,
    }


def original_range(mapping: list[list[int]], start: int, end: int) -> tuple[int, int]:
    if not 0 <= start < end <= len(mapping):
        raise ValueError("Rango normalizado inválido")
    return mapping[start][0], mapping[end - 1][1]
