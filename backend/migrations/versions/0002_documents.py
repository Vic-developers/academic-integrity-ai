"""Gestión documental y cola durable con RLS."""

import uuid

from alembic import op
from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def uid() -> str:
    return str(uuid.uuid4())


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        ForeignKeyConstraint(["institution_id", "teacher_id"], ["memberships.institution_id", "memberships.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    teacher_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        ForeignKeyConstraint(["institution_id", "course_id"], ["courses.institution_id", "courses.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("institution_id", "course_id", "student_id"),
        ForeignKeyConstraint(["institution_id", "course_id"], ["courses.institution_id", "courses.id"]),
        ForeignKeyConstraint(["institution_id", "student_id"], ["memberships.institution_id", "memberships.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        ForeignKeyConstraint(["institution_id", "owner_id"], ["memberships.institution_id", "memberships.id"]),
        ForeignKeyConstraint(["institution_id", "uploader_id"], ["memberships.institution_id", "memberships.id"]),
        ForeignKeyConstraint(["institution_id", "assignment_id"], ["assignments.institution_id", "assignments.id"]),
        CheckConstraint("state IN ('received','extracting','completed','partial','failed','cancelled')"),
        Index("ix_documents_tenant_created", "institution_id", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36))
    owner_id: Mapped[str] = mapped_column(String(36))
    uploader_id: Mapped[str] = mapped_column(String(36))
    assignment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(24), default="received")
    error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Version(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("institution_id", "id"),
        UniqueConstraint("institution_id", "document_id", "ordinal"),
        ForeignKeyConstraint(
            ["institution_id", "document_id"], ["documents.institution_id", "documents.id"], ondelete="CASCADE"
        ),
        CheckConstraint("size > 0 AND ordinal > 0"),
        Index("ix_versions_tenant_hash", "institution_id", "sha256"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(String(36))
    ordinal: Mapped[int] = mapped_column(default=1)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(8))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    extractor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Fragment(Base):
    __tablename__ = "document_fragments"
    __table_args__ = (
        UniqueConstraint("institution_id", "version_id", "ordinal"),
        ForeignKeyConstraint(
            ["institution_id", "version_id"],
            ["document_versions.institution_id", "document_versions.id"],
            ondelete="CASCADE",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(String(36))
    ordinal: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(250), nullable=True)
    original: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text)
    mapping: Mapped[list] = mapped_column(JSON)
    locations: Mapped[list] = mapped_column(JSON)
    sentences: Mapped[list] = mapped_column(JSON)


class DocumentJob(Base):
    __tablename__ = "document_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "version_id"],
            ["document_versions.institution_id", "document_versions.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("institution_id", "version_id", "kind"),
        CheckConstraint("kind IN ('extract','purge') AND attempts >= 0"),
        CheckConstraint("state IN ('pending','running','done','failed','cancelled')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(12), default="extract")
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


revision = "0002_documents"
down_revision = "0001_identity"
branch_labels = depends_on = None
TABLES = [
    "courses",
    "assignments",
    "enrollments",
    "documents",
    "document_versions",
    "document_fragments",
    "document_jobs",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.reflect(bind=bind, only=["institutions", "memberships"], extend_existing=True)
    Base.metadata.create_all(bind, tables=[Base.metadata.tables[t] for t in TABLES])
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING (institution_id = current_setting('app.institution_id', true)) WITH CHECK (institution_id = current_setting('app.institution_id', true))"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO aid_app")
    op.execute("""CREATE FUNCTION public.claim_document_job(token text) RETURNS TABLE(job_id varchar, tenant_id varchar)
        LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        UPDATE public.document_jobs SET state='running', attempts=attempts+1,
          lease_until=now()+interval '120 seconds', lease_token=token
        WHERE id = (SELECT id FROM public.document_jobs
          WHERE (state='pending' OR (state='running' AND lease_until<now())) AND attempts<3
          ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
        RETURNING id, institution_id $$""")
    op.execute("REVOKE ALL ON FUNCTION public.claim_document_job(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.claim_document_job(text) TO aid_app")
    op.execute("""CREATE FUNCTION public.fail_exhausted_document_jobs() RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
        BEGIN
          UPDATE public.documents d SET state='failed',error_code='worker_retries_exhausted'
          FROM public.document_versions v,public.document_jobs j
          WHERE d.id=v.document_id AND d.institution_id=v.institution_id
          AND v.id=j.version_id AND v.institution_id=j.institution_id
          AND j.kind='extract' AND j.state='running' AND j.attempts>=3 AND j.lease_until<now()
          AND d.deleted_at IS NULL AND d.state NOT IN ('cancelled','completed','partial');
          UPDATE public.document_jobs SET state='failed'
          WHERE state='running' AND attempts>=3 AND lease_until<now();
        END $$""")
    op.execute("REVOKE ALL ON FUNCTION public.fail_exhausted_document_jobs() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.fail_exhausted_document_jobs() TO aid_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION public.fail_exhausted_document_jobs()")
    op.execute("DROP FUNCTION public.claim_document_job(text)")
    for name in reversed(TABLES):
        op.drop_table(name)
