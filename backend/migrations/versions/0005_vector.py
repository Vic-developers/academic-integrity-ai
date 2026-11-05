"""Private vector cache and exact, prefiltered pgvector infrastructure; no model activation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType

revision = "0005_vector"
down_revision = "0004_review"
branch_labels = depends_on = None


class FrozenVector384(UserDefinedType):
    def get_col_spec(self, **kw):
        return "vector(384)"


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_unique_constraint(
        "uq_fragment_tenant_version_id", "document_fragments", ["institution_id", "version_id", "id"]
    )
    op.create_table(
        "semantic_vectors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("institution_id", sa.String(36), nullable=False),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("fragment_id", sa.String(36), nullable=False),
        sa.Column("model_key", sa.String(64), nullable=False),
        sa.Column("chunker_version", sa.String(64), nullable=False),
        sa.Column("original_start", sa.Integer(), nullable=False),
        sa.Column("original_end", sa.Integer(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("fragment_sha256", sa.String(64), nullable=False),
        sa.Column("embedding", FrozenVector384(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["institution_id", "version_id", "fragment_id"],
            ["document_fragments.institution_id", "document_fragments.version_id", "document_fragments.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "institution_id",
            "fragment_id",
            "model_key",
            "chunker_version",
            "original_start",
            "original_end",
            name="uq_semantic_vector_passage",
        ),
        sa.CheckConstraint(
            "original_start >= 0 AND original_end > original_start AND original_end-original_start <= 4096",
            name="ck_semantic_range",
        ),
        sa.CheckConstraint(
            "model_key ~ '^[0-9a-f]{64}$' AND input_sha256 ~ '^[0-9a-f]{64}$' AND fragment_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_semantic_hashes",
        ),
        sa.CheckConstraint("chunker_version ~ '^[a-z0-9._-]{1,64}$'", name="ck_semantic_chunker"),
        sa.CheckConstraint("abs(vector_norm(embedding)-1) < 0.0001", name="ck_semantic_unit_vector"),
    )
    op.create_index(
        "ix_semantic_scope", "semantic_vectors", ["institution_id", "model_key", "chunker_version", "version_id"]
    )
    op.execute("ALTER TABLE semantic_vectors ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE semantic_vectors FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON semantic_vectors USING (institution_id=current_setting('app.institution_id',true)) WITH CHECK (institution_id=current_setting('app.institution_id',true))"
    )
    op.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON semantic_vectors TO aid_app")


def downgrade():
    op.drop_table("semantic_vectors")
    op.drop_constraint("uq_fragment_tenant_version_id", "document_fragments", type_="unique")
