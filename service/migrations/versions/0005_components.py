"""add components table

Revision ID: 0005_components
Revises: 0004_note_public
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_components"
down_revision = "0004_note_public"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("components",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("location", sa.String(400), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_components_project", "components", ["project_id"])
    op.create_index("ix_components_kind", "components", ["kind"])

    # NOTIFY trigger so websocket clients get live updates
    op.execute("""
    CREATE TRIGGER components_notify
    AFTER INSERT OR UPDATE OR DELETE ON components
    FOR EACH ROW EXECUTE FUNCTION atrium_notify();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS components_notify ON components;")
    op.drop_index("ix_components_kind", "components")
    op.drop_index("ix_components_project", "components")
    op.drop_table("components")
