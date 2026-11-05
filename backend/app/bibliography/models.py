from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.models import uid


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
