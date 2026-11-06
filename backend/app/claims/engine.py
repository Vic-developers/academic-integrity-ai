"""Bounded, deterministic extraction and lexical retrieval. Scores never imply entailment."""

import hashlib
import re
import unicodedata
from collections import defaultdict, Counter
from app.bibliography.extraction import HEADING, extract as extract_references
from app.documents.normalization import normalize

VERSION = "claim-candidates-lexical-v1"
STOP = set(
    "el la los las un una unos unas de del al a y o en por para que se con sin es son fue fueron ser como según este esta estos estas su sus lo más menos the a an and or of in to for is are was were be by with without that this these those as".split()
)
SIGNALS = re.compile(
    r"\d|\b(?:aument\w*|reduc\w*|demuestr\w*|indic\w*|afirm\w*|evidenci\w*|provoc\w*|caus\w*|produce\w*|mejor\w*|disminu\w*|increment\w*|supports?|increases?|reduces?|causes?|shows?|suggests?)\b",
    re.I,
)


def words(text):
    return set(
        w for w in re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()) if len(w) > 2 and w not in STOP
    )


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def evidence(fragment, start, end):
    original = fragment["original"][start:end]
    return {
        "fragment_id": fragment["id"],
        "page": fragment["page"],
        "paragraph": fragment["paragraph"],
        "original_start": start,
        "original_end": end,
        "text": original,
        "span_sha256": digest(original),
        "fragment_sha256": digest(fragment["original"]),
        "offset_unit": "unicode_code_points",
    }


def sentence_spans(fragments):
    for f in fragments:
        raw = f["original"]
        limit = len(raw)
        base = 0
        stop = False
        for line in raw.splitlines(keepends=True):
            if HEADING.fullmatch(unicodedata.normalize("NFKC", line.strip())):
                limit = base
                stop = True
                break
            base += len(line)
        value = raw[:limit]
        start = 0
        for match in re.finditer(r"(?<!\d)[.!?](?:\s+|$)|(?<=\d)[.!?](?!\d)(?:\s+|$)|\n+", value):
            end = match.end()
            a, b = start, end
            while a < b and value[a].isspace():
                a += 1
            while b > a and value[b - 1].isspace():
                b -= 1
            if a < b:
                yield f, a, b
            start = end
        if start < len(value):
            a = start
            while a < len(value) and value[a].isspace():
                a += 1
            if a < len(value):
                yield f, a, len(value.rstrip())
        if stop:
            return


def analyze(target, sources):
    if (
        sum(len(f["original"]) for f in target) + sum(len(f["original"]) for s in sources for f in s["fragments"])
        > 1_000_000
    ):
        raise ValueError("claim_text_budget")
    reference_limits = []
    try:
        references = extract_references(target)
    except ValueError as exc:
        if str(exc) != "bibliography_text_budget":
            raise
        references = {"citations": [], "references": []}
        reference_limits.append("citation_context_text_budget")
    source_passages = []
    index = defaultdict(list)
    limits = list(reference_limits)
    for source in sources:
        for f, a, b in sentence_spans(source["fragments"]):
            if b - a > 2000:
                limits.append("source_passage_too_long")
                continue
            tokens = words(f["original"][a:b])
            if len(tokens) < 3:
                continue
            if len(source_passages) >= 5000:
                limits.append("source_passage_budget")
                break
            item = {"source_id": source["id"], "span": evidence(f, a, b), "tokens": tokens}
            position = len(source_passages)
            source_passages.append(item)
            for word in tokens:
                index[word].append(position)
    claims = []
    operations = 0
    for f, a, b in sentence_spans(target):
        raw = f["original"][a:b]
        if (
            raw.endswith("?")
            or raw.startswith(("¿", "?"))
            or len(re.findall(r"\w+", raw)) < 8
            or not SIGNALS.search(raw)
        ):
            continue
        if len(raw) > 2000:
            limits.append("claim_text_too_long")
            continue
        if len(claims) >= 100:
            limits.append("claim_budget")
            break
        tokens = words(raw)
        counts = Counter()
        for word in sorted(tokens):
            posting = index.get(word, [])
            if operations + len(posting) > 200000:
                limits.append("retrieval_budget")
                break
            operations += len(posting)
            counts.update(posting)
        candidates = []
        for position, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
            if count < 3:
                continue
            passage = source_passages[position]
            candidates.append(
                {
                    "source_id": passage["source_id"],
                    "span": passage["span"],
                    "method": "lexical_overlap_not_entailment",
                    "shared_terms": count,
                    "query_terms": len(tokens),
                    "normalized_claim_occurs": normalize(raw)[0] in normalize(passage["span"]["text"])[0],
                }
            )
            if len(candidates) >= 3:
                break
        linked = []
        for citation in references["citations"]:
            if any(
                span["fragment_id"] == f["id"] and span["original_start"] < b and span["original_end"] > a
                for span in citation["spans"]
            ):
                linked.append(
                    {
                        "label": citation["label"],
                        "state": citation["state"],
                        "reference_candidates": [
                            {"ordinal": r["ordinal"], "title": r["fields"]["title"], "dois": r["fields"]["dois"]}
                            for r in references["references"]
                            if r["ordinal"] in citation["references"]
                        ],
                    }
                )
        claims.append(
            {
                "origin": "heuristic_candidate",
                "span": evidence(f, a, b),
                "candidates": candidates,
                "citation_context": linked,
                "evidence_state": "candidates_retrieved"
                if candidates
                else "no_selected_sources"
                if not sources
                else "no_candidate_in_bounded_search",
                "automatic_verdict": "not_assessed",
            }
        )
    return {
        "engine": VERSION,
        "claims": claims,
        "source_passages_indexed": len(source_passages),
        "operations": operations,
        "limitations": sorted(
            set(
                limits
                + [
                    "heuristic_candidates_require_human_review",
                    "lexical_overlap_is_not_support",
                    "no_automatic_entailment_model",
                    "citation_links_are_candidates",
                ]
            )
        ),
        "partial": bool(limits),
    }
