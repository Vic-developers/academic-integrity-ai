from sqlalchemy import CheckConstraint, ForeignKeyConstraint, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.models import uid


class StyleAttestation(Base):
    __tablename__ = "style_attestations"
    __table_args__ = (
        UniqueConstraint("institution_id", "version_id"),
        ForeignKeyConstraint(
            ["institution_id", "version_id"],
            ["document_versions.institution_id", "document_versions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["institution_id", "student_id"], ["memberships.institution_id", "memberships.id"]),
        CheckConstraint("revision>=1"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    active: Mapped[bool] = mapped_column(default=True)
    revision: Mapped[int] = mapped_column(default=1)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    history: Mapped[list] = mapped_column(JSON, default=list)
