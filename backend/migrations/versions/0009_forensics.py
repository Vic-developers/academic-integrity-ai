"""Frozen forensic style attestation schema."""

import uuid

from alembic import op
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def uid():
    return str(uuid.uuid4())


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


revision = "0009_forensics"
down_revision = "0007_claims"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.reflect(bind=bind, only=["memberships", "document_versions"], extend_existing=True)
    Base.metadata.create_all(bind, tables=[Base.metadata.tables["style_attestations"]])
    op.execute("ALTER TABLE style_attestations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE style_attestations FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON style_attestations USING (institution_id=current_setting('app.institution_id',true)) WITH CHECK (institution_id=current_setting('app.institution_id',true))"
    )
    op.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON style_attestations TO aid_app")


def downgrade():
    op.drop_table("style_attestations")
