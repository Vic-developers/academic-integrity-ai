"""Fixed-host metadata adapters. A failed lookup is never evidence of an invented source."""

import hashlib
import json
import urllib.error
import urllib.parse
import os
import sys
import base64
import subprocess
from pathlib import Path
import time
from redis import Redis
from redis.exceptions import RedisError
from app.config import settings
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from app.bibliography.extraction import canonical_doi, normalized


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Unexpected metadata text type")
    parser = PlainText()
    parser.feed(str(value))
    return " ".join("".join(parser.parts).split())[:2000]


def http_request(url):
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    for name in [
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "https_proxy",
        "http_proxy",
        "all_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    ]:
        if name in os.environ:
            env[name] = os.environ[name]
    try:
        process = subprocess.run(
            [sys.executable, "-m", "app.bibliography.http_child"],
            input=json.dumps({"url": url}).encode(),
            capture_output=True,
            timeout=6,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        if process.returncode or len(process.stdout) > 400000:
            raise ValueError("Invalid transport output")
        result = json.loads(process.stdout)
        if result.get("network_error"):
            raise ValueError("Network unavailable")
        return result["status"], {"Retry-After": result["retry_after"]}, base64.b64decode(result["body"], validate=True)
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        raise urllib.error.URLError("Bibliographic transport unavailable") from exc


@dataclass(frozen=True)
class Lookup:
    state: str
    provider: str
    doi: str
    attempted: bool = False
    http_status: int | None = None
    metadata: dict | None = None
    response_text: str | None = None
    response_sha256: str | None = None
    retrieved_at: str | None = None
    retry_after: int | None = None


class Provider:
    def __init__(self, name, *, enabled=False, api_key="", transport=None):
        if name not in {"crossref", "openalex"}:
            raise ValueError("Unsupported bibliography provider")
        self.name, self.enabled, self.api_key, self.transport = name, enabled, api_key, transport

    def lookup(self, doi):
        doi = canonical_doi(doi)
        if not doi:
            raise ValueError("Invalid DOI")
        if not self.enabled:
            return Lookup("disabled", self.name, doi)
        if self.name == "openalex" and not self.api_key:
            return Lookup("not_configured", self.name, doi)
        url = (
            "https://api.crossref.org/works/"
            if self.name == "crossref"
            else "https://api.openalex.org/works/https://doi.org/"
        ) + urllib.parse.quote(doi, safe="")
        if self.name == "openalex":
            url += "?" + urllib.parse.urlencode({"api_key": self.api_key})
        if self.transport is None:
            try:
                with Redis.from_url(settings().redis_url, socket_timeout=1, socket_connect_timeout=1) as client:
                    deadline = time.monotonic() + 1.2
                    while not client.set("bibliography:rate:" + self.name, "1", nx=True, px=1000):
                        if time.monotonic() >= deadline:
                            return Lookup("rate_limited_local", self.name, doi)
                        time.sleep(0.1)
            except RedisError:
                return Lookup("unavailable", self.name, doi)
        try:
            if self.transport:
                status, headers, body = self.transport(url)
            else:
                status, headers, body = http_request(url)
        except (urllib.error.URLError, TimeoutError, OSError):
            return Lookup("unavailable", self.name, doi, True)
        if status == 404:
            return Lookup("not_found", self.name, doi, True, status)
        if status == 429:
            retry = headers.get("Retry-After", "")
            return Lookup(
                "rate_limited",
                self.name,
                doi,
                True,
                status,
                retry_after=min(3600, int(retry)) if str(retry).isdigit() else None,
            )
        if status != 200:
            return Lookup("unauthorized" if status in {401, 403} else "provider_error", self.name, doi, True, status)
        if len(body) > 262144:
            return Lookup("response_too_large", self.name, doi, True, status)
        try:
            raw = body.decode("utf-8")
            data = json.loads(raw)
            if self.api_key and any(
                secret in candidate
                for secret in {self.api_key, urllib.parse.quote(self.api_key, safe="")}
                for candidate in [raw, json.dumps(data, ensure_ascii=False)]
            ):
                raise ValueError("Response echoed a provider credential")
            if self.name == "crossref":
                row = data["message"]
                identity = canonical_doi(row.get("DOI", ""))
                titles = row.get("title")
                if not isinstance(titles, list) or not titles or not isinstance(titles[0], str):
                    raise ValueError("Invalid title contract")
                title = clean(titles[0])
                authors = [clean(p.get("family", "")) for p in row.get("author", [])[:50] if p.get("family")]
                years = sorted(
                    {
                        int(row[k]["date-parts"][0][0])
                        for k in ["published", "published-print", "published-online", "issued"]
                        if row.get(k, {}).get("date-parts") and row[k]["date-parts"][0]
                    }
                )
                venue = clean((row.get("container-title") or [""])[0])
                publisher = clean(row.get("publisher", ""))
            else:
                row = data
                identity = canonical_doi(row.get("doi", ""))
                title = clean(row.get("title") or row.get("display_name") or "")
                authors = [
                    clean(p["author"]["display_name"])
                    for p in row.get("authorships", [])[:50]
                    if p.get("author", {}).get("display_name")
                ]
                years = [int(row["publication_year"])] if row.get("publication_year") else []
                venue = clean(((row.get("primary_location") or {}).get("source") or {}).get("display_name", ""))
                publisher = None
            if identity != doi or not title:
                raise ValueError("Provider identity not verified")
            meta = {
                "doi": identity,
                "title": title,
                "authors": authors,
                "years": years,
                "venue": venue or None,
                "publisher": publisher or None,
            }
        except (ValueError, KeyError, TypeError, IndexError, AttributeError, RecursionError):
            return Lookup("invalid_response", self.name, doi, True, status)
        return Lookup(
            "found",
            self.name,
            doi,
            True,
            status,
            meta,
            raw,
            hashlib.sha256(body).hexdigest(),
            datetime.now(timezone.utc).isoformat(),
        )


def compare(reference, metadata):
    fields = reference["fields"]
    checks = []
    for name in ["title", "year", "authors", "venue", "publisher"]:
        printed = fields.get(name)
        observed = metadata.get("years" if name == "year" else name)
        if not printed or not observed:
            checks.append({"field": name, "state": "not_compared", "printed": printed, "observed": observed})
            continue
        if name == "year":
            same = printed in observed
        elif name == "authors":
            # Only surnames explicitly parsed before the first comma; multiple authors remain incomplete.
            surname = normalized(printed.split(",")[0])
            same = bool(observed) and (
                surname == normalized(observed[0]) or normalized(observed[0]).endswith(" " + surname)
            )
        else:
            same = normalized(str(printed)) == normalized(str(observed))
        checks.append(
            {
                "field": name,
                "state": "partial_equal" if name == "authors" and same else "equal" if same else "different",
                "printed": printed,
                "observed": observed,
            }
        )
    state = (
        "inconsistent"
        if any(c["state"] == "different" for c in checks)
        else "verified"
        if all(c["state"] == "equal" for c in checks)
        else "partially_verified"
    )
    return {
        "state": state,
        "checks": checks,
        "interpretation": "metadata_comparison_requires_human_review_not_a_plagiarism_judgment",
    }
