"""Auditorías literales, fuentes explícitas y evidencias."""

import uuid
from alembic import op

from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        UniqueConstraint("institution_id", "requester_id", "idempotency_key"),
        ForeignKeyConstraint(["institution_id", "requester_id"], ["memberships.institution_id", "memberships.id"]),
        ForeignKeyConstraint(
            ["institution_id", "target_version_id"], ["document_versions.institution_id", "document_versions.id"]
        ),
        CheckConstraint("state IN ('pending','running','completed','partial','failed','cancelled','invalidated')"),
        Index("ix_audits_tenant_created", "institution_id", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    requester_id: Mapped[str] = mapped_column(String(36))
    target_version_id: Mapped[str] = mapped_column(String(36))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    engine_version: Mapped[str] = mapped_column(String(80))
    config: Mapped[dict] = mapped_column(JSON)
    target_snapshot: Mapped[dict] = mapped_column(JSON)
    coverage: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditSource(Base):
    __tablename__ = "audit_sources"
    __table_args__ = (
        UniqueConstraint("institution_id", "audit_id", "id"),
        UniqueConstraint("institution_id", "audit_id", "version_id"),
        ForeignKeyConstraint(
            ["institution_id", "audit_id"], ["audits.institution_id", "audits.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["institution_id", "version_id"], ["document_versions.institution_id", "document_versions.id"]
        ),
        CheckConstraint("state IN ('pending','compared','partial','skipped','error')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    audit_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(String(36))
    snapshot: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "audit_id"], ["audits.institution_id", "audits.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["institution_id", "audit_id", "source_id"],
            ["audit_sources.institution_id", "audit_sources.audit_id", "audit_sources.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "target_start >= 0 AND target_end > target_start AND source_start >= 0 AND source_end > source_start AND word_count >= 8"
        ),
        Index("ix_findings_tenant_audit", "institution_id", "audit_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36))
    audit_id: Mapped[str] = mapped_column(String(36))
    source_id: Mapped[str] = mapped_column(String(36))
    category: Mapped[str] = mapped_column(String(40), default="textual_exact_normalized")
    review_state: Mapped[str] = mapped_column(String(20), default="pending")
    target_start: Mapped[int]
    target_end: Mapped[int]
    source_start: Mapped[int]
    source_end: Mapped[int]
    word_count: Mapped[int]
    evidence: Mapped[dict] = mapped_column(JSON)


class AuditJob(Base):
    __tablename__ = "audit_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "audit_id"], ["audits.institution_id", "audits.id"], ondelete="CASCADE"
        ),
        UniqueConstraint("institution_id", "audit_id"),
        CheckConstraint("state IN ('pending','running','done','failed','cancelled') AND attempts >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    audit_id: Mapped[str] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


revision = "0003_literal"
down_revision = "0002_documents"
branch_labels = depends_on = None
TABLES = ["audits", "audit_sources", "findings", "audit_jobs"]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.reflect(bind=bind, only=["memberships", "document_versions"], extend_existing=True)
    Base.metadata.create_all(bind, tables=[Base.metadata.tables[t] for t in TABLES])
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING (institution_id=current_setting('app.institution_id',true)) WITH CHECK (institution_id=current_setting('app.institution_id',true))"
        )
        op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {table} TO aid_app")
    op.execute("""CREATE FUNCTION public.claim_audit_job(token text) RETURNS TABLE(job_id varchar,tenant_id varchar)
        LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
        UPDATE public.audit_jobs SET state='running',attempts=attempts+1,lease_token=token,lease_until=now()+interval '120 seconds'
        WHERE id=(SELECT id FROM public.audit_jobs
          WHERE (state='pending' OR (state='running' AND lease_until<now())) AND attempts<3
          ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
        RETURNING id,institution_id $$""")
    op.execute("REVOKE ALL ON FUNCTION public.claim_audit_job(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.claim_audit_job(text) TO aid_app")
    op.execute("""CREATE FUNCTION public.fail_exhausted_audit_jobs() RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
        BEGIN
          UPDATE public.audits a SET state='failed',error_code='worker_retries_exhausted',finished_at=now()
          FROM public.audit_jobs j WHERE a.id=j.audit_id AND a.institution_id=j.institution_id
          AND j.state='running' AND j.attempts>=3 AND j.lease_until<now() AND a.state IN ('pending','running');
          UPDATE public.audit_jobs SET state='failed' WHERE state='running' AND attempts>=3 AND lease_until<now();
        END $$""")
    op.execute("REVOKE ALL ON FUNCTION public.fail_exhausted_audit_jobs() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.fail_exhausted_audit_jobs() TO aid_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION public.fail_exhausted_audit_jobs()")
    op.execute("DROP FUNCTION public.claim_audit_job(text)")
    for table in reversed(TABLES):
        op.drop_table(table)
