"""Deterministic literal retrieval. Fingerprints propose; real token comparison verifies."""

import hashlib
import re
from collections import defaultdict, deque
from dataclasses import dataclass

ENGINE_VERSION = "literal-winnow-v1"
K_GRAM = 5
WINDOW = 4
MIN_WORDS = 8
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class Token:
    value: str
    fragment: str
    start: int
    end: int
    word: bool


def tokenize(fragments: list[dict]) -> list[Token]:
    return [
        Token(m.group(), f["id"], m.start(), m.end(), bool(re.fullmatch(r"\w+", m.group())))
        for f in fragments
        for m in TOKEN_PATTERN.finditer(f["normalized"])
    ]


def gram_hash(values: list[str]) -> int:
    digest = hashlib.blake2b(digest_size=8)
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return int.from_bytes(digest.digest(), "big")


def fingerprints(tokens: list[Token], k: int = K_GRAM, window: int = WINDOW) -> list[tuple[int, int]]:
    hashes = [gram_hash([t.value for t in tokens[i : i + k]]) for i in range(max(0, len(tokens) - k + 1))]
    if not hashes:
        return []
    width = min(window, len(hashes))
    candidates: deque[int] = deque()
    selected = []
    last = -1
    for index, value in enumerate(hashes):
        while candidates and candidates[0] <= index - width:
            candidates.popleft()
        while candidates and hashes[candidates[-1]] >= value:
            candidates.pop()  # Rightmost minimum for ties.
        candidates.append(index)
        if index >= width - 1 and candidates[0] != last:
            last = candidates[0]
            selected.append((hashes[last], last))
    return selected


class BudgetReached(Exception):
    pass


class Budget:
    def __init__(self, seeds: int, checks: int):
        self.max_seeds, self.max_checks = seeds, checks
        self.seeds = self.checks = 0

    def seed(self) -> None:
        self.seeds += 1
        if self.seeds > self.max_seeds:
            raise BudgetReached("seed_budget")

    def equal(self, left: str, right: str) -> bool:
        self.checks += 1
        if self.checks > self.max_checks:
            raise BudgetReached("comparison_budget")
        return left == right


def compare(
    target_fragments: list[dict],
    sources: list[dict],
    *,
    min_words: int = MIN_WORDS,
    max_seeds: int = 50_000,
    max_checks: int = 2_000_000,
    max_findings: int = 500,
) -> dict:
    target = tokenize(target_fragments)
    target_words = sum(t.word for t in target)
    budget = Budget(max_seeds, max_checks)
    target_index = defaultdict(list)
    if target_words >= min_words:
        for fingerprint, position in fingerprints(target):
            target_index[fingerprint].append(position)
    results, coverage = [], []
    reason = "target_below_minimum_words" if target_words < min_words else None
    if reason:
        coverage = [{"id": source["id"], "state": "skipped", "reason": reason} for source in sources]
    else:
        for source in sources:
            tokens = tokenize(source["fragments"])
            if not any(t.word for t in tokens):
                coverage.append({"id": source["id"], "state": "skipped", "reason": "no_extractable_text"})
                continue
            covered: dict[int, list[tuple[int, int]]] = defaultdict(list)
            row = {"id": source["id"], "state": "compared", "reason": None}
            try:
                for fingerprint, s in fingerprints(tokens):
                    for q in target_index.get(fingerprint, []):
                        budget.seed()
                        diagonal = s - q
                        if any(a <= q < b for a, b in covered[diagonal]):
                            continue
                        if not all(budget.equal(target[q + i].value, tokens[s + i].value) for i in range(K_GRAM)):
                            continue
                        left = 0
                        while (
                            q - left - 1 >= 0
                            and s - left - 1 >= 0
                            and budget.equal(target[q - left - 1].value, tokens[s - left - 1].value)
                        ):
                            left += 1
                        right = K_GRAM
                        while (
                            q + right < len(target)
                            and s + right < len(tokens)
                            and budget.equal(target[q + right].value, tokens[s + right].value)
                        ):
                            right += 1
                        start, end = q - left, q + right
                        covered[diagonal].append((start, end))
                        while start < end and not target[start].word:
                            start += 1
                        while end > start and not target[end - 1].word:
                            end -= 1
                        words = sum(t.word for t in target[start:end])
                        if words < min_words:
                            continue
                        if len(results) >= max_findings:
                            raise BudgetReached("findings_budget")
                        results.append(
                            {
                                "source_id": source["id"],
                                "target_start": start,
                                "target_end": end,
                                "source_start": s + start - q,
                                "source_end": s + end - q,
                                "words": words,
                            }
                        )
            except BudgetReached as exc:
                reason = str(exc)
                row["state"], row["reason"] = "partial", reason
            coverage.append(row)
            if reason:
                break
        processed = {row["id"] for row in coverage}
        coverage.extend(
            {"id": s["id"], "state": "skipped", "reason": "budget_exhausted"}
            for s in sources
            if s["id"] not in processed
        )
    # Union prevents double-counting a target word appearing in multiple sources or overlapping runs.
    matched = set()
    for result in results:
        matched.update(i for i in range(result["target_start"], result["target_end"]) if target[i].word)
    return {
        "findings": results,
        "sources": coverage,
        "partial_reason": reason,
        "summary": {
            "target_words": target_words,
            "matched_words": len(matched),
            "seed_pairs_checked": min(budget.seeds, max_seeds),
            "token_comparisons": min(budget.checks, max_checks),
            "target_fingerprints": sum(map(len, target_index.values())),
        },
        "engine_version": ENGINE_VERSION,
    }
