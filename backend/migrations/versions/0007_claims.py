"""Claim candidates, selected sources, human assessments and durable jobs."""

from alembic import op
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
import uuid


class Base(DeclarativeBase):
    pass


def uid():
    return str(uuid.uuid4())


class ClaimRun(Base):
    __tablename__ = "claim_runs"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        UniqueConstraint("institution_id", "id", "version_id"),
        UniqueConstraint("institution_id", "requester_id", "idempotency_key"),
        ForeignKeyConstraint(["institution_id", "requester_id"], ["memberships.institution_id", "memberships.id"]),
        ForeignKeyConstraint(
            ["institution_id", "version_id"], ["document_versions.institution_id", "document_versions.id"]
        ),
        CheckConstraint("state IN ('pending','running','completed','partial','failed','cancelled','invalidated')"),
        Index("ix_claim_runs_scope", "institution_id", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36))
    requester_id: Mapped[str] = mapped_column(String(36))
    version_id: Mapped[str] = mapped_column(String(36))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    target_snapshot: Mapped[dict] = mapped_column(JSON)
    config: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClaimSource(Base):
    __tablename__ = "claim_sources"
    __table_args__ = (
        UniqueConstraint("institution_id", "run_id", "id"),
        UniqueConstraint("institution_id", "run_id", "version_id"),
        ForeignKeyConstraint(
            ["institution_id", "run_id"], ["claim_runs.institution_id", "claim_runs.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["institution_id", "version_id"], ["document_versions.institution_id", "document_versions.id"]
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36))
    run_id: Mapped[str] = mapped_column(String(36))
    version_id: Mapped[str] = mapped_column(String(36))
    snapshot: Mapped[dict] = mapped_column(JSON)


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "run_id", "version_id"],
            ["claim_runs.institution_id", "claim_runs.id", "claim_runs.version_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["institution_id", "version_id", "fragment_id"],
            ["document_fragments.institution_id", "document_fragments.version_id", "document_fragments.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("institution_id", "run_id", "fragment_id", "original_start", "original_end"),
        CheckConstraint("original_start>=0 AND original_end>original_start AND original_end-original_start<=2000"),
        CheckConstraint(
            "review_state IN ('unreviewed','supported','contradicted','partially_supported','not_verifiable','insufficient_source') AND review_revision>=0"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36))
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(String(36))
    fragment_id: Mapped[str] = mapped_column(String(36))
    original_start: Mapped[int]
    original_end: Mapped[int]
    ordinal: Mapped[int]
    evidence: Mapped[dict] = mapped_column(JSON)
    review_state: Mapped[str] = mapped_column(String(24), default="unreviewed")
    review_revision: Mapped[int] = mapped_column(default=0)
    review_log: Mapped[list] = mapped_column(JSON, default=list)


class ClaimJob(Base):
    __tablename__ = "claim_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "run_id"], ["claim_runs.institution_id", "claim_runs.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("institution_id", "run_id"),
        CheckConstraint("state IN ('pending','running','done','failed','cancelled') AND attempts>=0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


revision = "0007_claims"
down_revision = "0006_bibliography"
branch_labels = depends_on = None
TABLES = ["claim_runs", "claim_sources", "claims", "claim_jobs"]


def upgrade():
    bind = op.get_bind()
    Base.metadata.reflect(
        bind=bind, only=["memberships", "document_versions", "document_fragments"], extend_existing=True
    )
    Base.metadata.create_all(bind, tables=[Base.metadata.tables[t] for t in TABLES])
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING (institution_id=current_setting('app.institution_id',true)) WITH CHECK (institution_id=current_setting('app.institution_id',true))"
        )
        op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {table} TO aid_app")
    op.execute("""CREATE FUNCTION public.claim_statement_job(token text) RETURNS TABLE(job_id varchar,tenant_id varchar)
    LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    UPDATE public.claim_jobs SET state='running',attempts=attempts+1,lease_token=token,lease_until=now()+interval '120 seconds'
    WHERE id=(SELECT id FROM public.claim_jobs WHERE (state='pending' OR (state='running' AND lease_until<now())) AND attempts<3 ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
    RETURNING id,institution_id $$""")
    op.execute("""CREATE FUNCTION public.fail_exhausted_statement_jobs() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    BEGIN
    UPDATE public.claim_runs r SET state='failed',error_code='worker_retries_exhausted',finished_at=now() FROM public.claim_jobs j WHERE r.id=j.run_id AND r.institution_id=j.institution_id AND j.state='running' AND j.attempts>=3 AND j.lease_until<now() AND r.state IN ('pending','running');
    UPDATE public.claim_jobs SET state='failed' WHERE state='running' AND attempts>=3 AND lease_until<now();
    END $$""")
    for function in ["claim_statement_job(text)", "fail_exhausted_statement_jobs()"]:
        op.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO aid_app")


def downgrade():
    op.execute("DROP FUNCTION public.fail_exhausted_statement_jobs()")
    op.execute("DROP FUNCTION public.claim_statement_job(text)")
    for table in reversed(TABLES):
        op.drop_table(table)
