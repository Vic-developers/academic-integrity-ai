"""Conservative APA/numeric candidates and original-codepoint evidence; not a citation-style validator."""

import hashlib
import re
import unicodedata

VERSION = "bibliography-local-v1"
DOI = re.compile(r'10\.\d{4,9}/[^\s<>"{}]+', re.I)
HEADING = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:referencias(?: bibliográficas)?|bibliografía|references|works cited)\s*:?$", re.I
)
STOP = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:anexos?|apéndices?|appendix|appendices|agradecimientos|acknowledgments)\s*:?$", re.I
)
APA = re.compile(r"^(.{2,200}?)\s*\(((?:19|20)\d{2})[a-z]?\)\s*\.\s*(.+)$")
START = re.compile(r"^(?:\[\d{1,3}\]|\d{1,3}[.)])\s+|^.{2,160}?\(((?:19|20)\d{2})[a-z]?\)\s*\.")


def normalized(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def canonical_doi(value):
    if not isinstance(value, str) or len(value) > 512:
        return None
    value = (
        value.strip()
        .casefold()
        .removeprefix("https://doi.org/")
        .removeprefix("http://doi.org/")
        .removeprefix("doi:")
        .strip()
    )
    value = value.rstrip(".,;:")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    while value.endswith("]") and value.count("]") > value.count("["):
        value = value[:-1]
    if len(value) > 255 or not re.fullmatch(r"10\.\d{4,9}/[!-~]+", value, re.I):
        return None
    return value.casefold()


def spans(fragments, start, end):
    result = []
    base = 0
    for f in fragments:
        a, b = max(0, start - base), min(len(f["original"]), end - base)
        if a < b:
            text = f["original"][a:b]
            result.append(
                {
                    "fragment_id": f["id"],
                    "page": f["page"],
                    "paragraph": f["paragraph"],
                    "original_start": a,
                    "original_end": b,
                    "text": text[:2000],
                    "text_truncated": len(text) > 2000,
                    "span_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "fragment_sha256": hashlib.sha256(f["original"].encode()).hexdigest(),
                }
            )
        base += len(f["original"]) + 1
    return result[:50]


def fields(raw):
    text = " ".join(raw.split())
    number = None
    num = re.match(r"^(?:\[(\d{1,3})\]|(\d{1,3})[.)])\s+", text)
    if num:
        number = int(num.group(1) or num.group(2))
        text = text[num.end() :]
    match = APA.match(text)
    authors = year = title = venue = None
    if match:
        authors = match[1].strip()
        year = int(match[2])
        rest = match[3]
        title = rest.split(". ", 1)[0].rstrip(".")
        if ". " in rest:
            venue_text = (
                re.split(r"https?://|doi\s*:", rest.split(". ", 1)[1], maxsplit=1, flags=re.I)[0].strip().rstrip(".")
            )
            venue = re.split(r",\s*\d", venue_text, maxsplit=1)[0].strip() or None
    dois = list(dict.fromkeys(d for m in DOI.finditer(text) if (d := canonical_doi(m.group()))))
    return {
        "authors": authors,
        "year": year,
        "title": title,
        "venue": venue,
        "publisher": None,
        "number": number,
        "dois": dois,
        "parser": "apa_candidate" if match else "unstructured_candidate",
        "missing_fields": [
            name for name, value in [("authors", authors), ("year", year), ("title", title)] if not value
        ],
    }


def extract(fragments):
    whole = "\n".join(f["original"] for f in fragments)
    if len(whole) > 500_000:
        raise ValueError("bibliography_text_budget")
    lines = []
    base = 0
    for line in whole.splitlines(keepends=True):
        value = line.strip()
        a = base + len(line) - len(line.lstrip())
        b = base + len(line.rstrip())
        lines.append((value, a, b))
        base += len(line)
    heading = next(
        (i for i, (line, _, __) in enumerate(lines) if HEADING.fullmatch(unicodedata.normalize("NFKC", line))), None
    )
    reasons = []
    ranges = []
    if heading is None:
        reasons.append("bibliography_heading_not_found")
        ranges = [(m.start(), m.end(), "doi_mention") for m in DOI.finditer(whole) if canonical_doi(m.group())]
        body_end = len(whole)
    else:
        body_end = lines[heading][1]
        active = None
        for value, a, b in lines[heading + 1 :]:
            if STOP.fullmatch(unicodedata.normalize("NFKC", value)):
                break
            if not value:
                continue
            if active is None:
                active = [a, b]
            elif START.match(value):
                ranges.append((*active, "reference_candidate"))
                active = [a, b]
            else:
                active[1] = b
        if active:
            ranges.append((*active, "reference_candidate"))
    if not ranges:
        reasons.append("no_reference_candidates")
    if len(ranges) > 200:
        reasons.append("reference_budget")
    refs = []
    for index, (a, b, kind) in enumerate(ranges[:200], 1):
        if b - a > 8192:
            b = a + 8192
            reasons.append("reference_text_budget")
        raw = whole[a:b]
        parsed = fields(raw)
        refs.append(
            {
                "ordinal": index,
                "kind": kind,
                "text": raw,
                "fields": parsed,
                "spans": spans(fragments, a, b),
                "duplicate_of": None,
                "citation_state": "not_assessed" if heading is None else "not_seen_in_supported_patterns",
            }
        )
    seen = {}
    for ref in refs:
        key = ("doi", tuple(ref["fields"]["dois"])) if ref["fields"]["dois"] else ("text", normalized(ref["text"]))
        if key in seen:
            ref["duplicate_of"] = seen[key]
        else:
            seen[key] = ref["ordinal"]
    citations = []
    if heading is not None:
        body = whole[:body_end]
        for match in re.finditer(r"\[(\d{1,3}(?:\s*[,;–-]\s*\d{1,3}){0,19})\]", body):
            values = match[1]
            numbers = []
            for part in re.split(r"[,;]", values):
                ends = re.split(r"[-–]", part)
                a = int(ends[0])
                b = int(ends[-1])
                if b < a or b - a > 20:
                    continue
                numbers.extend(range(a, b + 1))
            for number in sorted(set(numbers)):
                if len(citations) >= 500:
                    break
                linked = [r for r in refs if r["fields"]["number"] == number]
                for r in linked:
                    r["citation_state"] = "seen_in_supported_pattern"
                citations.append(
                    {
                        "kind": "numeric",
                        "label": str(number),
                        "state": "matched" if len(linked) == 1 else "ambiguous" if linked else "unmatched_candidate",
                        "references": [r["ordinal"] for r in linked],
                        "spans": spans(fragments, match.start(), match.end()),
                    }
                )
            if len(citations) >= 500:
                break
        for match in re.finditer(r"\(([^()\n]{1,100}?),\s*((?:19|20)\d{2})[a-z]?\)", body):
            name = normalized(match[1].split(";")[-1]).split(" et al")[0]
            linked = [
                r
                for r in refs
                if r["fields"]["year"] == int(match[2])
                and r["fields"]["authors"]
                and normalized(r["fields"]["authors"].split(",")[0]) == name
            ]
            for r in linked:
                r["citation_state"] = "seen_in_supported_pattern"
            citations.append(
                {
                    "kind": "author_year",
                    "label": match.group(),
                    "state": "matched" if len(linked) == 1 else "ambiguous" if linked else "unmatched_candidate",
                    "references": [r["ordinal"] for r in linked],
                    "spans": spans(fragments, match.start(), match.end()),
                }
            )
            if len(citations) >= 500:
                break
    if len(citations) >= 500:
        reasons.append("citation_budget")
    return {
        "extractor": VERSION,
        "offset_unit": "unicode_code_points_within_original_fragment",
        "references": refs,
        "citations": citations[:500],
        "limitations": sorted(
            set(
                reasons
                + [
                    "apa_numeric_heuristics_require_review",
                    "citation_scope_before_bibliography",
                    "publisher_not_inferred",
                ]
            )
        ),
        "local_partial": bool(reasons),
        "heading_found": heading is not None,
    }
