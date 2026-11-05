"""Explicit human review states with optimistic concurrency and retained history."""

from alembic import op
import sqlalchemy as sa

revision = "0004_review"
down_revision = "0003_literal"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("findings", sa.Column("review_revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("findings", sa.Column("review_log", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    op.create_check_constraint(
        "ck_finding_review",
        "findings",
        "review_revision >= 0 AND review_state IN ('pending','reviewed','justified','dismissed','confirmed')",
    )


def downgrade():
    op.drop_constraint("ck_finding_review", "findings", type_="check")
    op.drop_column("findings", "review_log")
    op.drop_column("findings", "review_revision")
