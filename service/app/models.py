from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid4())


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(120), nullable=False, unique=True)
    glyph_color = Column(String(20), nullable=False, default="#7A6F62")
    phase = Column(String(20), nullable=False, default="active")  # active|specced|stable|paused|shipped|retired
    vision = Column(Text, nullable=False, default="")
    journal = Column(Text, nullable=False, default="")
    template = Column(String(20), nullable=False, default="software")  # software|growth|services|investigation|portfolio
    public = Column(Boolean, nullable=False, default=False)
    slug = Column(String(60), nullable=True, unique=True)
    public_summary = Column(Text, nullable=False, default="")
    progress = Column(Integer, nullable=False, default=0)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    title = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="next")  # today|next|blocked|done|later
    effort = Column(String(40), nullable=True)  # free-form e.g. "~30m"
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    question = Column(String(500), nullable=False)
    options = Column(JSON, nullable=True, default=list)
    choice = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open|resolved|revisit
    public = Column(Boolean, nullable=False, default=False)
    revisit_by = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Note(Base):
    __tablename__ = "notes"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    target_type = Column(String(40), nullable=False)  # project|task|decision|atom|intel|session|workbench
    target_id = Column(String(120), nullable=False)
    body = Column(Text, nullable=False)
    tag = Column(String(20), nullable=False, default="@me")  # @claude|@me|?question|!blocked|idea
    status = Column(String(20), nullable=False, default="open")  # open|resolved|archived
    resolved_by = Column(String(40), nullable=True)  # claude|ryan
    resolved_summary = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class NoteThread(Base):
    __tablename__ = "note_thread"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    note_id = Column(UUID(as_uuid=False), ForeignKey("notes.id"), nullable=False)
    author = Column(String(40), nullable=False)  # claude|ryan
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelItem(Base):
    __tablename__ = "intel_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source = Column(String(40), nullable=False)  # observer|stale|forge|pattern|question
    body = Column(Text, nullable=False)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(120), nullable=True)
    severity = Column(String(20), nullable=False, default="low")  # low|medium|high
    status = Column(String(20), nullable=False, default="active")  # active|dismissed|promoted
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    decisions_made = Column(JSON, nullable=True, default=list)
    files_touched = Column(JSON, nullable=True, default=list)
    atoms_created = Column(JSON, nullable=True, default=list)
    transcript_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    actor = Column(String(40), nullable=False)  # claude|ryan|system
    action = Column(String(80), nullable=False)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(120), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Link(Base):
    __tablename__ = "links"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    from_type = Column(String(40), nullable=False)
    from_id = Column(String(120), nullable=False)
    to_type = Column(String(40), nullable=False)
    to_id = Column(String(120), nullable=False)
    link_type = Column(String(40), nullable=False, default="references")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Focus(Base):
    __tablename__ = "focus"
    id = Column(Integer, primary_key=True, default=1)
    current_project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AtomRef(Base):
    __tablename__ = "atom_refs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    atom_name = Column(String(200), nullable=False)
    ref_type = Column(String(40), nullable=False, default="uses")  # uses|defines|references
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class WorkbenchItem(Base):
    __tablename__ = "workbench_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True)  # null = global
    section = Column(String(40), nullable=False)  # hypothesis|question|plan|pattern|scratch
    body = Column(Text, nullable=False)
    tag = Column(String(20), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)



class Component(Base):
    """Generic project component. The 'kind' field varies by project template.
    Software:      module|service|library|integration|datastore|frontend|cli
    Growth:        channel|persona|funnel_stage|content_type|metric
    Services:      customer_segment|service_offering|tool|equipment|territory
    Investigation: source|location|witness|exhibit|theory
    Portfolio:     page|asset|story|skill|audience
    """
    __tablename__ = "components"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    name = Column(String(160), nullable=False)
    kind = Column(String(40), nullable=False)
    status = Column(String(20), nullable=False, default="planned")  # live|partial|planned|deprecated
    description = Column(Text, nullable=False, default="")
    location = Column(String(400), nullable=True)  # file path / URL / owner / source name
    metadata_json = Column(JSON, nullable=True)  # template-specific fields
    public = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Pattern(Base):
    __tablename__ = "patterns"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="candidate")  # candidate|promoted|deprecated
    candidate_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class PatternUse(Base):
    __tablename__ = "pattern_uses"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    pattern_id = Column(UUID(as_uuid=False), ForeignKey("patterns.id"), nullable=False)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    implementation_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
