import re
import unicodedata
from collections import Counter
from datetime import datetime
from statistics import median
from app.claims.engine import evidence, digest
from app.experimental_ai.features import FEATURES, measure

VERSION = "forensic-observations-v1"


def display(text):
    return "".join(
        f"\\u{ord(c):04X}" if unicodedata.category(c) in {"Cf", "Cc"} and c not in "\n\t" else c for c in text
    )


def analyze(fragments, metadata, extractor):
    if sum(len(f["original"]) for f in fragments) > 500000:
        raise ValueError("forensic_text_budget")
    flags = []
    counts = Counter()

    def add(kind, f, a, b, **detail):
        counts[kind] += 1
        if len(flags) < 250:
            span = evidence(f, a, b)
            flags.append({"kind": kind, "span": span, "display_text": display(span["text"]), **detail})

    for f in fragments:
        text = f["original"]
        for i, c in enumerate(text):
            category = unicodedata.category(c)
            if category == "Cf" or category == "Cc" and c not in "\n\r\t\f":
                add(
                    "format_or_control_character",
                    f,
                    i,
                    i + 1,
                    code_point=f"U+{ord(c):04X}",
                    unicode_name=unicodedata.name(c, "UNNAMED"),
                )
            elif c in "\u00a0\u202f":
                add("nonbreaking_space", f, i, i + 1, code_point=f"U+{ord(c):04X}", unicode_name=unicodedata.name(c))
            elif unicodedata.normalize("NFKC", c) != c:
                add(
                    "compatibility_normalization",
                    f,
                    i,
                    i + 1,
                    normalized=unicodedata.normalize("NFKC", c),
                    unicode_name=unicodedata.name(c, "UNNAMED"),
                )
        for word in re.finditer(r"[^\W\d_]+", text, re.UNICODE):
            scripts = {unicodedata.name(c, "").split(" ")[0] for c in word.group()} & {"LATIN", "CYRILLIC", "GREEK"}
            if len(scripts) > 1 and word.end() - word.start() <= 2000:
                add("mixed_letter_scripts", f, word.start(), word.end(), scripts=sorted(scripts))
        for loc in f.get("locations", []):
            a, b = loc.get("start", -1), loc.get("end", -1)
            if not isinstance(a, int) or not isinstance(b, int) or not 0 <= a < b <= len(text) or b - a > 2000:
                continue
            if loc.get("explicit_hidden") is True:
                add("explicit_hidden_run", f, a, b)
            if loc.get("explicit_white") is True or loc.get("all_characters_white") is True:
                add("white_text_color", f, a, b)
            size = loc.get("font_size_pt", loc.get("font_size_min_pt"))
            if isinstance(size, (int, float)) and 0 <= size <= 2:
                add("font_size_at_most_2pt", f, a, b, font_size_pt=size)
    fields = [
        {"name": display(str(k)), "value": str(v)[:1000], "display_value": display(str(v)[:1000])}
        for k, v in metadata.items()
        if k != "pages" and isinstance(v, (str, int, float, bool))
    ][:100]
    dates = {str(k).lower(): str(v) for k, v in metadata.items() if isinstance(v, str)}
    created = dates.get("created") or dates.get("creationdate")
    modified = dates.get("modified") or dates.get("moddate")
    date_observation = "not_compared"
    try:

        def parse(value):
            if value.startswith("D:"):
                # Only complete explicit UTC PDF dates are comparable here.
                if not re.fullmatch(r"D:\d{14}Z", value):
                    raise ValueError
                return datetime.strptime(value, "D:%Y%m%d%H%M%SZ")
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is not None:
                raise ValueError
            return parsed

        if created and modified:
            date_observation = (
                "modified_before_created" if parse(modified) < parse(created) else "no_reversal_in_parsed_dates"
            )
    except (ValueError, TypeError):
        pass
    return {
        "engine": VERSION,
        "metadata": fields,
        "date_observation": date_observation,
        "flags": flags,
        "counts": dict(counts),
        "flags_total": sum(counts.values()),
        "flags_returned": len(flags),
        "partial": sum(counts.values()) > 250,
        "format_inspection_available": bool(extractor and "/forensic-v1/" in extractor),
        "limitations": [
            "metadata_is_editable_context_not_authorship_proof",
            "flags_do_not_establish_intent_or_misconduct",
            "white_text_can_be_visible_on_colored_background",
            "explicit_docx_properties_only_inherited_styles_not_resolved",
            "no_pdf_render_mode_or_complete_hidden_layer_analysis",
            "unicode_characters_have_legitimate_language_and_formatting_uses",
            "per_character_nfkc_checks_not_all_sequence_normalization_changes",
            "metadata_values_may_have_been_truncated_by_extractor",
        ],
        "authorship_probability": None,
        "assessment": "observations_only",
    }


def style_comparison(target, baselines):
    texts = [target, *baselines]
    if sum(map(len, texts)) > 500000:
        raise ValueError("style_text_budget")
    results = [measure(t) for t in texts]
    if any(r["counts"]["tokens"] < 100 for r in results):
        raise ValueError("style_sample_below_100_tokens")
    if len(set(digest(t) for t in texts)) != len(texts):
        raise ValueError("duplicate_style_text")
    rows = []
    for feature in FEATURES:
        values = [r["values"][feature] for r in results[1:]]
        center = median(values)
        observed = results[0]["values"][feature]
        rows.append(
            {
                "feature": feature,
                "target": observed,
                "baseline_median": center,
                "baseline_min": min(values),
                "baseline_max": max(values),
                "difference": observed - center,
            }
        )
    return {
        "engine": VERSION,
        "feature_engine": results[0]["engine"],
        "target_text_sha256": results[0]["text_sha256"],
        "source_text_sha256": [r["text_sha256"] for r in results[1:]],
        "rows": rows,
        "assessment": "descriptive_comparison_only",
        "authorship_probability": None,
        "limitations": [
            "human_attestations_are_not_independent_authorship_verification",
            "two_baseline_documents_is_a_technical_floor_not_scientific_sufficiency",
            "differences_can_reflect_topic_length_editing_or_extraction",
            "no_syntactic_semantic_or_author_identity_classifier",
            "style_change_is_not_evidence_of_ai_use",
        ],
    }
