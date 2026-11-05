import hashlib
import json
from app.audits.engine import MIN_WORDS, tokenize
from app.documents.normalization import original_range


def snapshot(document, version) -> dict:
    return {
        "document_id": document.id,
        "version_id": version.id,
        "name": document.name,
        "sha256": version.sha256,
        "extractor": version.extractor,
        "extraction_state": document.state,
        "extraction_warnings": version.warnings,
        "source_kind": "institutional_document",
    }


def ranges(fragments: list[dict], start: int, end: int, tokens=None, by_id=None) -> list[dict]:
    tokens = tokenize(fragments) if tokens is None else tokens
    selected = tokens[start:end]
    by_id = {f["id"]: f for f in fragments} if by_id is None else by_id
    groups = []
    for token in selected:
        if not groups or groups[-1][0] != token.fragment:
            groups.append([token.fragment, token.start, token.end])
        else:
            groups[-1][2] = token.end
    result = []
    for id, a, b in groups:
        f = by_id[id]
        x, y = original_range(f["mapping"], a, b)
        original = f["original"][x:y]
        locations = [
            {k: v for k, v in loc.items() if k != "chars"}
            for loc in f["locations"]
            if "start" not in loc or loc.get("end", 0) > x and loc["start"] < y
        ]
        # Source geometry stays in its original coordinate system; no screen pixels are invented.
        result.append(
            {
                "fragment_id": id,
                "page": f["page"],
                "paragraph": f["paragraph"],
                "normalized_start": a,
                "normalized_end": b,
                "original_start": x,
                "original_end": y,
                "text": original[:2000],
                "text_truncated": len(original) > 2000,
                "span_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "fragment_sha256": hashlib.sha256(f["original"].encode()).hexdigest(),
                "locations": locations[:200],
                "locations_truncated": len(locations) > 200,
                "sentences": [i + 1 for i, s in enumerate(f["sentences"]) if s["end"] > x and s["start"] < y],
            }
        )
    return result


def make_evidence(
    target: list[dict],
    source: list[dict],
    match: dict,
    *,
    target_tokens=None,
    source_tokens=None,
    target_by_id=None,
    source_by_id=None,
) -> dict:
    target_tokens = tokenize(target) if target_tokens is None else target_tokens
    source_tokens = tokenize(source) if source_tokens is None else source_tokens
    if not (
        0 <= match["target_start"] < match["target_end"] <= len(target_tokens)
        and 0 <= match["source_start"] < match["source_end"] <= len(source_tokens)
    ):
        raise ValueError("Invalid token ranges")
    selected_target = target_tokens[match["target_start"] : match["target_end"]]
    selected_source = source_tokens[match["source_start"] : match["source_end"]]
    words = sum(t.word for t in selected_target)
    if words < MIN_WORDS or words != match["words"]:
        raise ValueError("Invalid verified word count")
    q_values = [t.value for t in selected_target]
    s_values = [t.value for t in selected_source]
    if q_values != s_values:
        raise ValueError("Unverified fingerprint collision")
    q = ranges(target, match["target_start"], match["target_end"], target_tokens, target_by_id)
    s = ranges(source, match["source_start"], match["source_end"], source_tokens, source_by_id)
    return {
        "comparison": "normalized_token_sequence",
        "token_sequence_sha256": hashlib.sha256(json.dumps(q_values, ensure_ascii=False).encode()).hexdigest(),
        "target_ranges": q,
        "source_ranges": s,
        "citation": "pending_review",
        "offset_unit": "unicode_code_points",
        "raw_equal": ("\n".join(r["text"] for r in q) == "\n".join(r["text"] for r in s))
        if all(not r["text_truncated"] for r in q + s)
        else None,
        "explanation": f"Se verificó una secuencia continua de {match['words']} palabras con los mismos signos y normalización Unicode/mayúsculas. Requiere revisar el contexto y la citación; no demuestra plagio.",
    }
