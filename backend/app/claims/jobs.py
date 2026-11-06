import json
import uuid
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from app.audits.jobs import fragments
from app.claims.engine import analyze, VERSION
from app.claims.models import ClaimRun, Claim, ClaimJob
from app.claims.service import authorized, lock_documents, requester
from app.db import context, engine
from app.security import now


def process_next():
    token = str(uuid.uuid4())
    with Session(engine) as db, db.begin():
        db.execute(text("SELECT public.fail_exhausted_statement_jobs()"))
        claimed = db.execute(text("SELECT * FROM public.claim_statement_job(:token)"), {"token": token}).first()
    if claimed is None:
        return False
    job_id, tenant = claimed
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        job = db.get(ClaimJob, job_id)
        run = db.get(ClaimRun, job.run_id)
        lock_documents(db, run)
        run = db.scalar(select(ClaimRun).where(ClaimRun.id == run.id).with_for_update())
        job = db.scalar(
            select(ClaimJob).where(ClaimJob.id == job_id).with_for_update().execution_options(populate_existing=True)
        )
        if job.state != "running" or job.lease_token != token or run.state not in {"pending", "running"}:
            return True
        try:
            member = requester(db, run)
            run, sources = authorized(db, member, run.id)
        except HTTPException:
            run.state, run.error_code, run.finished_at, job.state = "failed", "permission_revoked", now(), "failed"
            return True
        target = fragments(db, run.version_id)
        source_data = [{"id": s.id, "fragments": fragments(db, s.version_id)} for s in sources]
        partial_extraction = run.target_snapshot["extraction_state"] == "partial" or any(
            s.snapshot["extraction_state"] == "partial" for s in sources
        )
        run.state, run.started_at = "running", now()
        run_id = run.id
    result = {}
    error = None
    try:
        result = analyze(target, source_data)
        if len(json.dumps(result, ensure_ascii=False).encode()) > 4 * 1024 * 1024:
            raise ValueError("claim_evidence_budget")
    except ValueError as exc:
        error = str(exc) if str(exc) in {"claim_text_budget", "claim_evidence_budget"} else "claim_extraction_failed"
    except Exception:
        error = "claim_extraction_failed"
    with Session(engine) as db, db.begin():
        context(db, institution_id=tenant)
        run = db.get(ClaimRun, run_id)
        lock_documents(db, run)
        run = db.scalar(select(ClaimRun).where(ClaimRun.id == run_id).with_for_update())
        job = db.scalar(select(ClaimJob).where(ClaimJob.id == job_id).with_for_update())
        if job.state != "running" or job.lease_token != token or run.state != "running":
            return True
        try:
            member = requester(db, run)
            authorized(db, member, run.id)
        except HTTPException:
            error = "permission_revoked"
        if error:
            run.state, run.error_code, job.state = "failed", error, "failed"
            run.summary = {}
        else:
            db.execute(delete(Claim).where(Claim.run_id == run_id))
            for ordinal, item in enumerate(result["claims"], 1):
                span = item["span"]
                db.add(
                    Claim(
                        institution_id=tenant,
                        run_id=run_id,
                        version_id=run.version_id,
                        fragment_id=span["fragment_id"],
                        original_start=span["original_start"],
                        original_end=span["original_end"],
                        ordinal=ordinal,
                        evidence=item,
                    )
                )
            run.summary = {
                "engine": VERSION,
                "candidates_extracted": len(result["claims"]),
                "source_passages_indexed": result["source_passages_indexed"],
                "lexical_operations": result["operations"],
                "limitations": result["limitations"],
                "extraction_partial": partial_extraction,
                "automatic_assessments": 0,
            }
            run.state = "partial" if result["partial"] or partial_extraction else "completed"
            job.state = "done"
        run.finished_at = now()
    return True
