from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.models import uid


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
