"""add public/slug/public_summary to projects, public flag to decisions

Revision ID: 0003_public
Revises: 0002_template
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_public"
down_revision = "0002_template"
branch_labels = None
depends_on = None


def _slugify(name):
    s = "".join(c.lower() if c.isalnum() else "-" for c in name)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def upgrade() -> None:
    op.add_column("projects", sa.Column("public", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("slug", sa.String(60), nullable=True))
    op.add_column("projects", sa.Column("public_summary", sa.Text, nullable=False, server_default=""))
    op.create_unique_constraint("uq_projects_slug", "projects", ["slug"])

    op.add_column("decisions", sa.Column("public", sa.Boolean, nullable=False, server_default="false"))

    # backfill slugs from existing names
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM projects")).fetchall()
    for row in rows:
        slug = _slugify(row[1])
        conn.execute(sa.text("UPDATE projects SET slug = :slug WHERE id = :id"), {"slug": slug, "id": row[0]})


def downgrade() -> None:
    op.drop_column("decisions", "public")
    op.drop_constraint("uq_projects_slug", "projects")
    op.drop_column("projects", "public_summary")
    op.drop_column("projects", "slug")
    op.drop_column("projects", "public")
