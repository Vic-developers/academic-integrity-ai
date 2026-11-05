"""Tenant-private vector infrastructure; does not approve a model or activate inference."""

import json
import math
import struct
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType
from app.db import Base
from app.models import uid

DIMENSION = 384


def unit_vector(values) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != DIMENSION:
        raise ValueError("Vector must have 384 dimensions")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in values):
        raise ValueError("Vector coordinates must be finite numbers")
    try:
        values = [float(x) for x in values]
    except OverflowError as exc:
        raise ValueError("Vector coordinates exceed numerical bounds") from exc
    if not all(math.isfinite(x) for x in values):
        raise ValueError("Vector coordinates must be finite numbers")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError("Zero or overflowing vectors are not comparable")
    # pgvector stores float32. Canonicalize before checking immutable cache contents.
    return [struct.unpack("f", struct.pack("f", x / norm))[0] for x in values]


class Vector384(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return "vector(384)"

    def bind_processor(self, dialect):
        return lambda value: "[" + ",".join(format(x, ".9g") for x in unit_vector(value)) + "]"

    def result_processor(self, dialect, coltype):
        return lambda value: json.loads(value) if isinstance(value, str) else list(value)


class SemanticVector(Base):
    __tablename__ = "semantic_vectors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id", "version_id", "fragment_id"],
            ["document_fragments.institution_id", "document_fragments.version_id", "document_fragments.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "institution_id",
            "fragment_id",
            "model_key",
            "chunker_version",
            "original_start",
            "original_end",
            name="uq_semantic_vector_passage",
        ),
        CheckConstraint(
            "original_start >= 0 AND original_end > original_start AND original_end-original_start <= 4096",
            name="ck_semantic_range",
        ),
        CheckConstraint(
            "model_key ~ '^[0-9a-f]{64}$' AND input_sha256 ~ '^[0-9a-f]{64}$' AND fragment_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_semantic_hashes",
        ),
        CheckConstraint("chunker_version ~ '^[a-z0-9._-]{1,64}$'", name="ck_semantic_chunker"),
        CheckConstraint("abs(vector_norm(embedding)-1) < 0.0001", name="ck_semantic_unit_vector"),
        Index("ix_semantic_scope", "institution_id", "model_key", "chunker_version", "version_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36))
    version_id: Mapped[str] = mapped_column(String(36))
    fragment_id: Mapped[str] = mapped_column(String(36))
    model_key: Mapped[str] = mapped_column(String(64))
    chunker_version: Mapped[str] = mapped_column(String(64))
    original_start: Mapped[int]
    original_end: Mapped[int]
    input_sha256: Mapped[str] = mapped_column(String(64))
    fragment_sha256: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(Vector384())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
