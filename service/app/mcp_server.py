"""FastMCP tool surface — mounted at /mcp/. The 20 workspace_* tools."""
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .db import AsyncSessionLocal
from . import models, schemas

mcp = FastMCP("atrium-workspace")


async def _session() -> AsyncSession:
    return AsyncSessionLocal()


@mcp.tool()
async def workspace_session_init() -> dict:
    """Load active focus, open notes, recent events and decisions. Call at the start of every chat."""
    async with AsyncSessionLocal() as db:
        focus_row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
        focus_pid = focus_row.current_project_id if focus_row else None

        focus_project = None
        if focus_pid:
            p = (await db.execute(select(models.Project).where(models.Project.id == focus_pid))).scalar_one_or_none()
            if p:
                focus_project = {"id": p.id, "name": p.name, "phase": p.phase, "vision": p.vision}

        notes = (await db.execute(
            select(models.Note).where(models.Note.status == "open").order_by(desc(models.Note.created_at)).limit(20)
        )).scalars().all()

        events = (await db.execute(
            select(models.Event).order_by(desc(models.Event.created_at)).limit(15)
        )).scalars().all()

        decisions = (await db.execute(
            select(models.Decision).order_by(desc(models.Decision.created_at)).limit(10)
        )).scalars().all()

        return {
            "ok": True,
            "data": {
                "focus": focus_project,
                "open_notes": [{"id": n.id, "target": f"{n.target_type}:{n.target_id}", "tag": n.tag, "body": n.body} for n in notes],
                "recent_events": [{"actor": e.actor, "action": e.action, "target": f"{e.target_type}:{e.target_id}"} for e in events],
                "recent_decisions": [{"id": d.id, "project_id": d.project_id, "question": d.question, "choice": d.choice, "status": d.status} for d in decisions],
            }
        }


@mcp.tool()
async def workspace_set_focus(project_name: str) -> dict:
    """Set the currently focused project by name."""
    async with AsyncSessionLocal() as db:
        p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
        if not p:
            return {"ok": False, "error": f"project '{project_name}' not found"}
        focus_row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
        if focus_row is None:
            db.add(models.Focus(id=1, current_project_id=p.id))
        else:
            focus_row.current_project_id = p.id
        db.add(models.Event(actor="claude", action="focus_set", target_type="project", target_id=p.id))
        await db.commit()
        return {"ok": True, "data": {"focus_project_id": p.id, "focus_project_name": p.name}}


@mcp.tool()
async def workspace_list_projects(phase: Optional[str] = None) -> dict:
    """List projects, optionally filtered by phase (active|specced|stable|paused|shipped|retired)."""
    async with AsyncSessionLocal() as db:
        q = select(models.Project).order_by(models.Project.position, models.Project.name)
        if phase:
            q = q.where(models.Project.phase == phase)
        rows = (await db.execute(q)).scalars().all()
        return {"ok": True, "data": [{"id": p.id, "name": p.name, "phase": p.phase, "progress": p.progress} for p in rows]}


@mcp.tool()
async def workspace_get_project(name: str, full: bool = False) -> dict:
    """Get a project by name. If full=True, includes tasks, decisions, notes."""
    async with AsyncSessionLocal() as db:
        p = (await db.execute(select(models.Project).where(models.Project.name == name))).scalar_one_or_none()
        if not p:
            return {"ok": False, "error": "project not found"}

        data = {"id": p.id, "name": p.name, "phase": p.phase, "vision": p.vision, "journal": p.journal, "progress": p.progress}
        if full:
            tasks = (await db.execute(select(models.Task).where(models.Task.project_id == p.id))).scalars().all()
            decisions = (await db.execute(select(models.Decision).where(models.Decision.project_id == p.id))).scalars().all()
            notes = (await db.execute(select(models.Note).where(models.Note.target_type == "project", models.Note.target_id == p.id, models.Note.status == "open"))).scalars().all()
            data["tasks"] = [{"id": t.id, "title": t.title, "status": t.status, "effort": t.effort} for t in tasks]
            data["decisions"] = [{"id": d.id, "question": d.question, "choice": d.choice, "status": d.status} for d in decisions]
            data["open_notes"] = [{"id": n.id, "tag": n.tag, "body": n.body} for n in notes]

        return {"ok": True, "data": data}


@mcp.tool()
async def workspace_create_project(name: str, vision: str = "", glyph_color: str = "#7A6F62", phase: str = "active") -> dict:
    """Create a new project chamber."""
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(models.Project).where(models.Project.name == name))).scalar_one_or_none()
        if existing:
            return {"ok": False, "error": f"project '{name}' already exists"}
        p = models.Project(name=name, vision=vision, glyph_color=glyph_color, phase=phase)
        db.add(p)
        db.add(models.Event(actor="claude", action="project_created", target_type="project", target_id=p.id, payload={"name": name}))
        await db.commit()
        await db.refresh(p)
        return {"ok": True, "data": {"id": p.id, "name": p.name}}


@mcp.tool()
async def workspace_update_project_field(project_name: str, field: str, value: str) -> dict:
    """Update a single field on a project. Valid fields: vision, journal, phase, glyph_color, progress."""
    valid_fields = {"vision", "journal", "phase", "glyph_color", "progress"}
    if field not in valid_fields:
        return {"ok": False, "error": f"field must be one of {valid_fields}"}
    async with AsyncSessionLocal() as db:
        p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
        if not p:
            return {"ok": False, "error": "project not found"}
        if field == "progress":
            value = int(value)
        setattr(p, field, value)
        db.add(models.Event(actor="claude", action="project_updated", target_type="project", target_id=p.id, payload={field: value}))
        await db.commit()
        return {"ok": True, "data": {"project": project_name, field: value}}


@mcp.tool()
async def workspace_add_task(project_name: str, title: str, status: str = "next", effort: Optional[str] = None) -> dict:
    """Add a task to a project. Status: today|next|blocked|done|later."""
    async with AsyncSessionLocal() as db:
        p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
        if not p:
            return {"ok": False, "error": "project not found"}
        t = models.Task(project_id=p.id, title=title, status=status, effort=effort)
        db.add(t)
        db.add(models.Event(actor="claude", action="task_created", target_type="task", target_id=t.id, payload={"title": title, "project": project_name}))
        await db.commit()
        await db.refresh(t)
        return {"ok": True, "data": {"id": t.id, "title": title, "status": status}}


@mcp.tool()
async def workspace_move_task(task_id: str, status: str) -> dict:
    """Move a task to a different status."""
    async with AsyncSessionLocal() as db:
        t = (await db.execute(select(models.Task).where(models.Task.id == task_id))).scalar_one_or_none()
        if not t:
            return {"ok": False, "error": "task not found"}
        old = t.status
        t.status = status
        db.add(models.Event(actor="claude", action="task_moved", target_type="task", target_id=task_id, payload={"from": old, "to": status}))
        await db.commit()
        return {"ok": True, "data": {"id": task_id, "status": status, "previous": old}}


@mcp.tool()
async def workspace_log_decision(project_name: str, question: str, choice: str, reasoning: str, options: Optional[List[Dict[str, Any]]] = None) -> dict:
    """Log a decision against a project."""
    async with AsyncSessionLocal() as db:
        p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
        if not p:
            return {"ok": False, "error": "project not found"}
        d = models.Decision(project_id=p.id, question=question, choice=choice, reasoning=reasoning, options=options or [], status="resolved")
        db.add(d)
        db.add(models.Event(actor="claude", action="decision_logged", target_type="decision", target_id=d.id, payload={"question": question, "project": project_name}))
        await db.commit()
        await db.refresh(d)
        return {"ok": True, "data": {"id": d.id, "question": question, "choice": choice}}


@mcp.tool()
async def workspace_add_note(target_type: str, target_id: str, body: str, tag: str = "@me") -> dict:
    """Add a note. target_type: project|task|decision|atom|intel|session|workbench. tag: @claude|@me|?question|!blocked|idea."""
    valid_tags = {"@claude", "@me", "?question", "!blocked", "idea"}
    if tag not in valid_tags:
        return {"ok": False, "error": f"tag must be one of {valid_tags}"}
    async with AsyncSessionLocal() as db:
        n = models.Note(target_type=target_type, target_id=target_id, body=body, tag=tag)
        db.add(n)
        db.add(models.Event(actor="claude", action="note_added", target_type=target_type, target_id=target_id, payload={"tag": tag}))
        await db.commit()
        await db.refresh(n)
        return {"ok": True, "data": {"id": n.id, "target": f"{target_type}:{target_id}", "tag": tag}}


@mcp.tool()
async def workspace_resolve_note(note_id: str, summary: str) -> dict:
    """Mark a note as resolved with an annotation describing what was done."""
    from datetime import datetime, timezone
    async with AsyncSessionLocal() as db:
        n = (await db.execute(select(models.Note).where(models.Note.id == note_id))).scalar_one_or_none()
        if not n:
            return {"ok": False, "error": "note not found"}
        n.status = "resolved"
        n.resolved_by = "claude"
        n.resolved_summary = summary
        n.resolved_at = datetime.now(timezone.utc)
        db.add(models.Event(actor="claude", action="note_resolved", target_type="note", target_id=note_id, payload={"summary": summary}))
        await db.commit()
        return {"ok": True, "data": {"id": note_id, "status": "resolved", "summary": summary}}


@mcp.tool()
async def workspace_list_notes(status: str = "open", target_type: Optional[str] = None) -> dict:
    """List notes. Drives batch review."""
    async with AsyncSessionLocal() as db:
        q = select(models.Note).where(models.Note.status == status).order_by(desc(models.Note.created_at))
        if target_type:
            q = q.where(models.Note.target_type == target_type)
        rows = (await db.execute(q)).scalars().all()
        return {"ok": True, "data": [{"id": n.id, "target": f"{n.target_type}:{n.target_id}", "tag": n.tag, "body": n.body, "created_at": n.created_at.isoformat()} for n in rows]}


@mcp.tool()
async def workspace_emit_intel(source: str, body: str, target_type: Optional[str] = None, target_id: Optional[str] = None, severity: str = "low") -> dict:
    """Push an intelligence item into the right rail. Used by Observer, Forge, cron jobs."""
    async with AsyncSessionLocal() as db:
        i = models.IntelItem(source=source, body=body, target_type=target_type, target_id=target_id, severity=severity)
        db.add(i)
        await db.commit()
        await db.refresh(i)
        return {"ok": True, "data": {"id": i.id}}


@mcp.tool()
async def workspace_dismiss_intel(intel_id: str) -> dict:
    """Dismiss an intel item from the rail."""
    async with AsyncSessionLocal() as db:
        i = (await db.execute(select(models.IntelItem).where(models.IntelItem.id == intel_id))).scalar_one_or_none()
        if not i:
            return {"ok": False, "error": "intel item not found"}
        i.status = "dismissed"
        await db.commit()
        return {"ok": True, "data": {"id": intel_id, "status": "dismissed"}}


@mcp.tool()
async def workspace_add_workbench(section: str, body: str, project_name: Optional[str] = None, tag: Optional[str] = None) -> dict:
    """Add a workbench item. section: hypothesis|question|plan|pattern|scratch. project_name omitted = global workbench."""
    valid_sections = {"hypothesis", "question", "plan", "pattern", "scratch"}
    if section not in valid_sections:
        return {"ok": False, "error": f"section must be one of {valid_sections}"}
    async with AsyncSessionLocal() as db:
        project_id = None
        if project_name:
            p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
            if not p:
                return {"ok": False, "error": "project not found"}
            project_id = p.id
        item = models.WorkbenchItem(project_id=project_id, section=section, body=body, tag=tag)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return {"ok": True, "data": {"id": item.id, "section": section}}


@mcp.tool()
async def workspace_link(from_type: str, from_id: str, to_type: str, to_id: str, link_type: str = "references") -> dict:
    """Create a cross-reference link."""
    async with AsyncSessionLocal() as db:
        l = models.Link(from_type=from_type, from_id=from_id, to_type=to_type, to_id=to_id, link_type=link_type)
        db.add(l)
        await db.commit()
        await db.refresh(l)
        return {"ok": True, "data": {"id": l.id}}


@mcp.tool()
async def workspace_search(query: str, scope: Optional[str] = None) -> dict:
    """Full-text search across projects, decisions, notes, journal."""
    from sqlalchemy import or_
    async with AsyncSessionLocal() as db:
        like = f"%{query}%"
        results: List[Dict[str, Any]] = []

        if scope in (None, "projects"):
            rows = (await db.execute(select(models.Project).where(or_(models.Project.name.ilike(like), models.Project.vision.ilike(like), models.Project.journal.ilike(like))))).scalars().all()
            results.extend([{"type": "project", "id": p.id, "name": p.name, "match": "vision/journal"} for p in rows])

        if scope in (None, "decisions"):
            rows = (await db.execute(select(models.Decision).where(or_(models.Decision.question.ilike(like), models.Decision.reasoning.ilike(like))))).scalars().all()
            results.extend([{"type": "decision", "id": d.id, "question": d.question} for d in rows])

        if scope in (None, "notes"):
            rows = (await db.execute(select(models.Note).where(models.Note.body.ilike(like)))).scalars().all()
            results.extend([{"type": "note", "id": n.id, "body": n.body[:120]} for n in rows])

        return {"ok": True, "data": results, "count": len(results)}


@mcp.tool()
async def workspace_create_session(title: str, summary: str, project_name: Optional[str] = None, decisions_made: Optional[List[str]] = None, files_touched: Optional[List[str]] = None) -> dict:
    """Save a session summary at the end of a chat."""
    async with AsyncSessionLocal() as db:
        project_id = None
        if project_name:
            p = (await db.execute(select(models.Project).where(models.Project.name == project_name))).scalar_one_or_none()
            project_id = p.id if p else None
        s = models.Session(title=title, summary=summary, project_id=project_id, decisions_made=decisions_made or [], files_touched=files_touched or [])
        db.add(s)
        await db.commit()
        await db.refresh(s)
        return {"ok": True, "data": {"id": s.id, "title": title}}


@mcp.tool()
async def workspace_get_focus() -> dict:
    """Get the currently focused project."""
    async with AsyncSessionLocal() as db:
        focus_row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
        if not focus_row or not focus_row.current_project_id:
            return {"ok": True, "data": {"focus": None}}
        p = (await db.execute(select(models.Project).where(models.Project.id == focus_row.current_project_id))).scalar_one_or_none()
        return {"ok": True, "data": {"focus": {"id": p.id, "name": p.name, "phase": p.phase} if p else None}}
