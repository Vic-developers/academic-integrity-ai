from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.models import uid


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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    audit_id: Mapped[str] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
