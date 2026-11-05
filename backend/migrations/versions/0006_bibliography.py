"""Bibliographic runs, durable jobs and tenant-private metadata snapshots."""

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


class BibliographyRun(Base):
    __tablename__ = "bibliography_runs"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        UniqueConstraint("institution_id", "requester_id", "idempotency_key"),
        ForeignKeyConstraint(["institution_id", "requester_id"], ["memberships.institution_id", "memberships.id"]),
        ForeignKeyConstraint(
            ["institution_id", "version_id"], ["document_versions.institution_id", "document_versions.id"]
        ),
        CheckConstraint("state IN ('pending','running','completed','partial','failed','cancelled','invalidated')"),
        Index("ix_bibliography_runs_tenant_created", "institution_id", "created_at", "id"),
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
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BibliographyJob(Base):
    __tablename__ = "bibliography_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "run_id"],
            ["bibliography_runs.institution_id", "bibliography_runs.id"],
            ondelete="CASCADE",
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


revision = "0006_bibliography"
down_revision = "0005_vector"
branch_labels = depends_on = None
TABLES = ["bibliography_runs", "bibliography_jobs"]


def upgrade():
    op.execute("ALTER TABLE institutions ADD COLUMN bibliography_external_allowed boolean NOT NULL DEFAULT false")
    op.execute("GRANT UPDATE (bibliography_external_allowed) ON institutions TO aid_app")
    op.execute("""CREATE POLICY institutions_bibliography_write ON institutions FOR UPDATE
    USING (id=current_setting('app.institution_id',true) AND EXISTS (SELECT 1 FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.institution_id=institutions.id AND m.user_id=current_setting('app.user_id',true) AND m.active AND u.active AND m.role IN ('admin','superadmin')))
    WITH CHECK (id=current_setting('app.institution_id',true) AND EXISTS (SELECT 1 FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.institution_id=institutions.id AND m.user_id=current_setting('app.user_id',true) AND m.active AND u.active AND m.role IN ('admin','superadmin')))""")
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
    op.execute("""CREATE FUNCTION public.claim_bibliography_job(token text) RETURNS TABLE(job_id varchar,tenant_id varchar)
    LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    UPDATE public.bibliography_jobs SET state='running',attempts=attempts+1,lease_token=token,lease_until=now()+interval '120 seconds'
    WHERE id=(SELECT id FROM public.bibliography_jobs WHERE (state='pending' OR (state='running' AND lease_until<now())) AND attempts<3 ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
    RETURNING id,institution_id $$""")
    op.execute("""CREATE FUNCTION public.fail_exhausted_bibliography_jobs() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    BEGIN
    UPDATE public.bibliography_runs r SET state='failed',error_code='worker_retries_exhausted',finished_at=now() FROM public.bibliography_jobs j WHERE r.id=j.run_id AND r.institution_id=j.institution_id AND j.state='running' AND j.attempts>=3 AND j.lease_until<now() AND r.state IN ('pending','running');
    UPDATE public.bibliography_jobs SET state='failed' WHERE state='running' AND attempts>=3 AND lease_until<now();
    END $$""")
    for function in ["claim_bibliography_job(text)", "fail_exhausted_bibliography_jobs()"]:
        op.execute(f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO aid_app")


def downgrade():
    op.execute("DROP POLICY institutions_bibliography_write ON institutions")
    op.execute("REVOKE UPDATE (bibliography_external_allowed) ON institutions FROM aid_app")
    op.drop_column("institutions", "bibliography_external_allowed")
    op.execute("DROP FUNCTION public.fail_exhausted_bibliography_jobs()")
    op.execute("DROP FUNCTION public.claim_bibliography_job(text)")
    for table in reversed(TABLES):
        op.drop_table(table)
