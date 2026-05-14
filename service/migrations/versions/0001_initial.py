"""initial schema with notify triggers

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("glyph_color", sa.String(20), nullable=False, server_default="#7A6F62"),
        sa.Column("phase", sa.String(20), nullable=False, server_default="active"),
        sa.Column("vision", sa.Text, nullable=False, server_default=""),
        sa.Column("journal", sa.Text, nullable=False, server_default=""),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("tasks",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="next"),
        sa.Column("effort", sa.String(40)),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("decisions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("options", postgresql.JSONB),
        sa.Column("choice", sa.Text),
        sa.Column("reasoning", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("revisit_by", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("notes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tag", sa.String(20), nullable=False, server_default="@me"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("resolved_by", sa.String(40)),
        sa.Column("resolved_summary", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notes_target", "notes", ["target_type", "target_id"])
    op.create_index("ix_notes_status", "notes", ["status"])

    op.create_table("note_thread",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("note_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("notes.id"), nullable=False),
        sa.Column("author", sa.String(40), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("intel_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("target_type", sa.String(40)),
        sa.Column("target_id", sa.String(120)),
        sa.Column("severity", sa.String(20), nullable=False, server_default="low"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("decisions_made", postgresql.JSONB),
        sa.Column("files_touched", postgresql.JSONB),
        sa.Column("atoms_created", postgresql.JSONB),
        sa.Column("transcript_url", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("actor", sa.String(40), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40)),
        sa.Column("target_id", sa.String(120)),
        sa.Column("payload", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_events_created", "events", ["created_at"])

    op.create_table("links",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("from_type", sa.String(40), nullable=False),
        sa.Column("from_id", sa.String(120), nullable=False),
        sa.Column("to_type", sa.String(40), nullable=False),
        sa.Column("to_id", sa.String(120), nullable=False),
        sa.Column("link_type", sa.String(40), nullable=False, server_default="references"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("focus",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("current_project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("atom_refs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("atom_name", sa.String(200), nullable=False),
        sa.Column("ref_type", sa.String(40), nullable=False, server_default="uses"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("workbench_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id")),
        sa.Column("section", sa.String(40), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tag", sa.String(20)),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("patterns",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="candidate"),
        sa.Column("candidate_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table("pattern_uses",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("pattern_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("patterns.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("implementation_note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # LISTEN/NOTIFY trigger function
    op.execute("""
    CREATE OR REPLACE FUNCTION atrium_notify() RETURNS trigger AS $$
    DECLARE
      payload JSON;
    BEGIN
      payload := json_build_object(
        'event', TG_OP,
        'table', TG_TABLE_NAME,
        'id', COALESCE(NEW.id::text, OLD.id::text),
        'at', extract(epoch from now())
      );
      PERFORM pg_notify('atrium_events', payload::text);
      RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """)

    for tbl in ["projects", "tasks", "decisions", "notes", "intel_items", "workbench_items"]:
        op.execute(f"""
        CREATE TRIGGER {tbl}_notify
        AFTER INSERT OR UPDATE OR DELETE ON {tbl}
        FOR EACH ROW EXECUTE FUNCTION atrium_notify();
        """)


def downgrade() -> None:
    for tbl in ["projects", "tasks", "decisions", "notes", "intel_items", "workbench_items"]:
        op.execute(f"DROP TRIGGER IF EXISTS {tbl}_notify ON {tbl};")
    op.execute("DROP FUNCTION IF EXISTS atrium_notify();")

    for tbl in ["pattern_uses", "patterns", "workbench_items", "atom_refs", "focus", "links",
                "events", "sessions", "intel_items", "note_thread", "notes",
                "decisions", "tasks", "projects"]:
        op.drop_table(tbl)
