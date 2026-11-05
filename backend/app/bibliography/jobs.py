from dataclasses import asdict
import json
import time
import uuid
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.audits.jobs import fragments
from app.bibliography.extraction import extract
from app.bibliography.models import BibliographyJob, BibliographyRun
from app.bibliography.providers import Lookup, Provider, compare
from app.bibliography.service import authorized, lock_document, requester
from app.config import settings
from app.db import context, engine
from app.security import now
from app.models import Institution


class LookupInterrupted(RuntimeError):
    pass


def analyze(parts, config, providers, check_continue=None):
    result = extract(parts)
    cache = {}
    stopped_providers = {}
    start = time.monotonic()
    for ref in result["references"]:
        ref["lookups"] = []
        if not config["request_external"]:
            ref["verification_state"] = "not_requested"
            continue
        dois = ref["fields"]["dois"]
        if len(dois) != 1:
            ref["verification_state"] = "identifier_missing" if not dois else "identifier_ambiguous"
            continue
        doi = dois[0]
        if doi not in cache:
            if len(cache) >= 10 or time.monotonic() - start > 65:
                ref["verification_state"] = "lookup_budget"
                result["local_partial"] = True
                continue
            cache[doi] = []
            for name in config["providers"]:
                if providers[name].enabled and check_continue is not None and not check_continue():
                    raise LookupInterrupted()
                if name in stopped_providers:
                    lookup = Lookup(stopped_providers[name], name, doi)
                else:
                    lookup = providers[name].lookup(doi)
                    if lookup.state in {"rate_limited", "unauthorized", "unavailable", "provider_error"}:
                        stopped_providers[name] = lookup.state
                item = asdict(lookup)
                cache[doi].append(item)
        ref["lookups"] = [
            {
                **{k: v for k, v in item.items() if k != "response_text"},
                "comparison": compare(ref, item["metadata"]) if item["state"] == "found" else None,
            }
            for item in cache[doi]
        ]
        comparisons = [item["comparison"]["state"] for item in ref["lookups"] if item["comparison"]]
        ref["verification_state"] = (
            "inconsistent"
            if "inconsistent" in comparisons
            else "verified"
            if comparisons and all(s == "verified" for s in comparisons)
            else "partially_verified"
            if comparisons
            else "not_located_in_selected_providers"
            if ref["lookups"] and all(x["state"] == "not_found" for x in ref["lookups"])
            else "lookup_incomplete"
        )
    result["provider_snapshots"] = cache
    attempts = sum(item["attempted"] for values in cache.values() for item in values)
    verified = sum(any(item["state"] == "found" for item in r.get("lookups", [])) for r in result["references"])
    unresolved = (
        any(
            r["verification_state"]
            not in {"verified", "partially_verified", "inconsistent", "not_located_in_selected_providers"}
            for r in result["references"]
        )
        if config["request_external"]
        else False
    )
    partial = (
        result["local_partial"]
        or unresolved
        or any(
            item["state"] not in {"found", "not_found"}
            for ref in result["references"]
            for item in ref.get("lookups", [])
        )
    )
    summary = {
        "references": len(result["references"]),
        "doi_references": sum(bool(r["fields"]["dois"]) for r in result["references"]),
        "duplicate_candidates": sum(r["duplicate_of"] is not None for r in result["references"]),
        "unmatched_citation_candidates": sum(c["state"] == "unmatched_candidate" for c in result["citations"]),
        "uncited_reference_candidates": sum(
            r["citation_state"] == "not_seen_in_supported_patterns" for r in result["references"]
        ),
        "metadata_retrieved_references": verified,
        "provider_attempts": attempts,
        "external_requested": config["request_external"],
    }
    if len(json.dumps(result, ensure_ascii=False).encode()) > 8 * 1024 * 1024:
        raise ValueError("bibliography_evidence_budget")
    return result, summary, partial


def process_next(providers=None):
    token = str(uuid.uuid4())
    with Session(engine) as db, db.begin():
        db.execute(text("SELECT public.fail_exhausted_bibliography_jobs()"))
        claim = db.execute(text("SELECT * FROM public.claim_bibliography_job(:token)"), {"token": token}).first()
    if claim is None:
        return False
    job_id, tenant = claim
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        job = db.get(BibliographyJob, job_id)
        run = db.get(BibliographyRun, job.run_id)
        lock_document(db, run)
        run = db.scalar(select(BibliographyRun).where(BibliographyRun.id == run.id).with_for_update())
        job = db.scalar(
            select(BibliographyJob)
            .where(BibliographyJob.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job.state != "running" or job.lease_token != token or run.state not in {"pending", "running"}:
            return True
        try:
            member = requester(db, run)
            run = authorized(db, member, run.id)
        except HTTPException:
            run.state, run.error_code, run.finished_at, job.state = "failed", "permission_revoked", now(), "failed"
            return True
        institution_allowed = db.get(Institution, tenant).bibliography_external_allowed
        data = fragments(db, run.version_id)
        config = dict(run.config)
        run.state, run.started_at = "running", now()
        run_id = run.id
    error = None
    result = {}
    summary = {}
    partial = True
    cfg = settings()
    providers = providers or {
        name: Provider(
            name, enabled=cfg.bibliography_external_enabled, api_key=cfg.openalex_api_key if name == "openalex" else ""
        )
        for name in ["crossref", "openalex"]
    }
    if not institution_allowed:
        providers = {name: Provider(name) for name in ["crossref", "openalex"]}

    def check_continue():
        with Session(engine) as check_db, check_db.begin():
            context(check_db, institution_id=tenant)
            current_job = check_db.get(BibliographyJob, job_id)
            current_run = check_db.get(BibliographyRun, run_id)
            if current_job.state != "running" or current_job.lease_token != token or current_run.state != "running":
                return False
            if not check_db.get(Institution, tenant).bibliography_external_allowed:
                return False
            try:
                current_member = requester(check_db, current_run)
                authorized(check_db, current_member, run_id)
            except HTTPException:
                return False
            return True

    try:
        result, summary, partial = analyze(data, config, providers, check_continue)
    except LookupInterrupted:
        error = "permission_revoked"

    except ValueError as exc:
        error = (
            str(exc)
            if str(exc) in {"bibliography_text_budget", "bibliography_evidence_budget"}
            else "bibliography_failed"
        )
    except Exception:
        error = "bibliography_failed"
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        run = db.get(BibliographyRun, run_id)
        lock_document(db, run)
        run = db.scalar(select(BibliographyRun).where(BibliographyRun.id == run_id).with_for_update())
        job = db.scalar(select(BibliographyJob).where(BibliographyJob.id == job_id).with_for_update())
        if job.state != "running" or job.lease_token != token or run.state != "running":
            return True
        try:
            member = requester(db, run)
            authorized(db, member, run_id)
        except HTTPException:
            error = "permission_revoked"
        if error:
            run.state, run.error_code, job.state = "failed", error, "failed"
            run.result, run.summary = {}, {}
        else:
            run.state = "partial" if partial or run.target_snapshot["extraction_state"] == "partial" else "completed"
            run.result, run.summary, job.state = result, summary, "done"
        run.finished_at = now()
    return True
