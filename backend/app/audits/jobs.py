import json
import uuid
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from app.audits.engine import tokenize
from app.audits.evidence import make_evidence
from app.audits.models import Audit, AuditJob, Finding
from app.audits.providers import web_coverage
from app.audits.runner import run_engine
from app.audits.service import authorized_audit, lock_documents, requester
from app.db import context, engine
from app.documents.models import Fragment
from app.security import now


def fragments(db, version_id):
    return [
        {
            "id": f.id,
            "original": f.original,
            "normalized": f.normalized,
            "mapping": f.mapping,
            "locations": f.locations,
            "sentences": f.sentences,
            "page": f.page,
            "paragraph": f.paragraph,
        }
        for f in db.scalars(select(Fragment).where(Fragment.version_id == version_id).order_by(Fragment.ordinal))
    ]


def process_next() -> bool:
    token = str(uuid.uuid4())
    with Session(engine) as db, db.begin():
        db.execute(text("SELECT public.fail_exhausted_audit_jobs()"))
        claimed = db.execute(text("SELECT * FROM public.claim_audit_job(:token)"), {"token": token}).first()
    if claimed is None:
        return False
    job_id, tenant = claimed
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        job = db.get(AuditJob, job_id)
        audit_id = job.audit_id
        lock_documents(db, audit_id)
        audit = db.scalar(select(Audit).where(Audit.id == audit_id).with_for_update())
        job = db.scalar(
            select(AuditJob).where(AuditJob.id == job_id).with_for_update().execution_options(populate_existing=True)
        )
        if job.state != "running" or job.lease_token != token or audit.state not in {"pending", "running"}:
            return True
        try:
            member = requester(db, audit)
            audit, sources = authorized_audit(db, member, audit_id)
        except HTTPException:
            audit.state, audit.error_code, job.state, audit.finished_at = (
                "failed",
                "permission_revoked",
                "failed",
                now(),
            )
            return True
        target = fragments(db, audit.target_version_id)
        source_data = [{"id": s.id, "fragments": fragments(db, s.version_id)} for s in sources]
        config = dict(audit.config)
        partial_extraction = audit.target_snapshot["extraction_state"] == "partial" or any(
            s.snapshot["extraction_state"] == "partial" for s in sources
        )
        audit.state, audit.started_at = "running", now()
    error, result = None, None
    try:
        result = run_engine(
            {
                "target_fragments": target,
                "sources": source_data,
                "min_words": config["min_words"],
                "max_seeds": config["max_seeds"],
                "max_checks": config["max_checks"],
                "max_findings": config["max_findings"],
            }
        )
    except RuntimeError as exc:
        error = str(exc)
    except Exception:
        error = "engine_failed"
    web = web_coverage(config["request_web"], target)
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        lock_documents(db, audit_id)
        audit = db.scalar(select(Audit).where(Audit.id == audit_id).with_for_update())
        job = db.scalar(select(AuditJob).where(AuditJob.id == job_id).with_for_update())
        if job.state != "running" or job.lease_token != token or audit.state != "running":
            return True
        try:
            member = requester(db, audit)
            audit, sources = authorized_audit(db, member, audit_id)
        except HTTPException:
            audit.state, audit.error_code, job.state, audit.finished_at = (
                "failed",
                "permission_revoked",
                "failed",
                now(),
            )
            db.execute(delete(Finding).where(Finding.audit_id == audit_id))
            audit.summary, audit.coverage = {}, {}
            return True
        if error:
            audit.state, audit.error_code, job.state = "failed", error, "failed"
            audit.coverage = {
                "web": web,
                "local": {"state": "failed", "sources_selected": len(sources), "sources_compared": 0},
            }
        else:
            db.execute(delete(Finding).where(Finding.audit_id == audit_id))
            tt = tokenize(target)
            target_by_id = {f["id"]: f for f in target}
            source_by_id = {s["id"]: s["fragments"] for s in source_data}
            source_tokens = {s["id"]: tokenize(s["fragments"]) for s in source_data}
            source_fragments = {k: {f["id"]: f for f in value} for k, value in source_by_id.items()}
            matched = set()
            evidence_size, saved = 0, 0
            evidence_limited = False
            for match in result["findings"]:
                evidence = make_evidence(
                    target,
                    source_by_id[match["source_id"]],
                    match,
                    target_tokens=tt,
                    source_tokens=source_tokens[match["source_id"]],
                    target_by_id=target_by_id,
                    source_by_id=source_fragments[match["source_id"]],
                )
                evidence["observed_at"] = now().isoformat()
                evidence_size += len(json.dumps(evidence, ensure_ascii=False).encode())
                if evidence_size > 8 * 1024 * 1024:
                    evidence_limited = True
                    break
                db.add(
                    Finding(
                        institution_id=tenant,
                        audit_id=audit_id,
                        source_id=match["source_id"],
                        target_start=match["target_start"],
                        target_end=match["target_end"],
                        source_start=match["source_start"],
                        source_end=match["source_end"],
                        word_count=match["words"],
                        evidence=evidence,
                    )
                )
                matched.update(i for i in range(match["target_start"], match["target_end"]) if tt[i].word)
                saved += 1
            rows = {row["id"]: row for row in result["sources"]}
            for source in sources:
                row = rows[source.id]
                source.state, source.reason = row["state"], row["reason"]
                source.snapshot = {
                    **source.snapshot,
                    "consulted_at": audit.started_at.isoformat(),
                    "verification": "content_compared"
                    if source.state == "compared"
                    else "partial_comparison"
                    if source.state == "partial"
                    else "not_compared",
                }
            skipped = any(s.state in {"skipped", "partial", "error"} for s in sources)
            partial = bool(
                result["partial_reason"]
                or skipped
                or evidence_limited
                or partial_extraction
                or config["request_web"]
                and web["state"] != "completed"
            )
            audit.state = "partial" if partial else "completed"
            audit.error_code = result["partial_reason"] or ("evidence_budget" if evidence_limited else None)
            audit.summary = {**result["summary"], "matched_words": len(matched), "findings": saved}
            audit.coverage = {
                "local": {
                    "state": "partial"
                    if partial_extraction or skipped or result["partial_reason"] or evidence_limited
                    else "completed",
                    "sources_selected": len(sources),
                    "sources_compared": sum(s.state == "compared" for s in sources),
                    "sources_skipped": sum(s.state == "skipped" for s in sources),
                    "extraction_partial": partial_extraction,
                    "evidence_limited": evidence_limited,
                },
                "web": web,
            }
            job.state = "done"
        audit.finished_at = now()
    return True
