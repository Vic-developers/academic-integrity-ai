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
from app.db import Base
from app.models import uid


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
