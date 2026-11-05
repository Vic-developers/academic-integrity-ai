"""Provider boundary. No configured provider means no outbound queries or fabricated sources."""

from dataclasses import dataclass
from typing import Protocol
import re


@dataclass(frozen=True)
class SearchResult:
    state: str
    provider: str | None
    queries_sent: int
    results: tuple
    reason: str | None = None


class SearchProvider(Protocol):
    def search(self, queries: list[str]) -> SearchResult: ...


class UnavailableSearchProvider:
    def search(self, queries: list[str]) -> SearchResult:
        return SearchResult("unavailable", None, 0, (), "No hay proveedor autorizado y configurado")


def build_queries(fragments: list[dict], limit: int = 5) -> list[str]:
    result = []
    for f in fragments:
        words = re.findall(r"\w+", f["normalized"])
        if len(words) >= 8:
            query = '"' + " ".join(words[:15]) + '"'
            if query not in result:
                result.append(query)
        if len(result) >= limit:
            break
    return result


def web_coverage(requested: bool, fragments: list[dict], provider: SearchProvider | None = None) -> dict:
    if not requested:
        return {
            "requested": False,
            "state": "not_requested",
            "queries_generated": 0,
            "queries_sent": 0,
            "sources_retrieved": 0,
            "sources_verified": 0,
        }
    queries = build_queries(fragments)
    result = (provider or UnavailableSearchProvider()).search(queries)
    return {
        "requested": True,
        "state": result.state if result.state in {"unavailable", "failed", "rate_limited"} else "discovery_only",
        "provider": result.provider,
        "queries_generated": len(queries),
        "queries_sent": result.queries_sent,
        "results_returned": len(result.results),
        "sources_retrieved": 0,
        "sources_verified": 0,
        "reason": result.reason,
    }
