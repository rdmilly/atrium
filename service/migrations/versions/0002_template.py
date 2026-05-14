"""add template column to projects

Revision ID: 0002_template
Revises: 0001_initial
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_template"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


TEMPLATE_BY_PROJECT = {
    "Helix Cortex": "software",
    "MemBrain": "software",
    "Atrium": "software",
    "MillyGate": "software",
    "Provisioner": "software",
    "helixcode.app": "software",
    "Memory ContextEngine": "software",
    "Content Pipeline": "software",
    "Shanghai Pipeline": "software",
    "ClientFlow": "software",
    "Lead Pipeline": "growth",
    "AOS Investigations": "investigation",
    "Confidence Lighting": "services",
    "Postiz": "software",
    "MW Dev Site": "portfolio",
    "Quiet Conviction": "portfolio",
}


def upgrade() -> None:
    op.add_column("projects", sa.Column("template", sa.String(20), nullable=False, server_default="software"))
    # set per-project templates
    for name, template in TEMPLATE_BY_PROJECT.items():
        op.execute(f"UPDATE projects SET template = '{template}' WHERE name = '{name}'")


def downgrade() -> None:
    op.drop_column("projects", "template")
