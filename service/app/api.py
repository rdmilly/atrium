import asyncio
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc

from .db import get_db, engine
from . import models, schemas
from .settings import settings

router = APIRouter(prefix="/api/v1")


# ---------- auth dependency ----------
async def require_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[7:]
    if token != settings.api_token:
        raise HTTPException(status_code=403, detail="invalid token")


# ---------- health ----------
@router.get("/health")
async def health():
    return {"ok": True, "service": "atrium", "version": "0.1.0"}


# ---------- session init ----------
@router.get("/session/init", response_model=schemas.SessionInitOut, dependencies=[Depends(require_token)])
async def session_init(db: AsyncSession = Depends(get_db)):
    focus_row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
    focus = schemas.FocusOut(current_project_id=focus_row.current_project_id if focus_row else None)

    notes_rows = (await db.execute(
        select(models.Note).where(models.Note.status == "open").order_by(desc(models.Note.created_at)).limit(20)
    )).scalars().all()

    events_rows = (await db.execute(
        select(models.Event).order_by(desc(models.Event.created_at)).limit(15)
    )).scalars().all()

    decisions_rows = (await db.execute(
        select(models.Decision).order_by(desc(models.Decision.created_at)).limit(10)
    )).scalars().all()

    return schemas.SessionInitOut(
        focus=focus,
        open_notes=[schemas.NoteOut.model_validate(n) for n in notes_rows],
        recent_events=[{"actor": e.actor, "action": e.action, "target": f"{e.target_type}:{e.target_id}", "at": e.created_at.isoformat()} for e in events_rows],
        recent_decisions=[schemas.DecisionOut.model_validate(d) for d in decisions_rows],
    )


# ---------- focus ----------
@router.get("/focus", response_model=schemas.FocusOut, dependencies=[Depends(require_token)])
async def get_focus(db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
    return schemas.FocusOut(current_project_id=row.current_project_id if row else None)


@router.post("/focus", response_model=schemas.FocusOut, dependencies=[Depends(require_token)])
async def set_focus(payload: schemas.FocusSet, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Focus).where(models.Focus.id == 1))).scalar_one_or_none()
    if row is None:
        row = models.Focus(id=1, current_project_id=payload.current_project_id)
        db.add(row)
    else:
        row.current_project_id = payload.current_project_id
    db.add(models.Event(actor="system", action="focus_set", target_type="focus", target_id=str(payload.current_project_id or "")))
    await db.commit()
    return schemas.FocusOut(current_project_id=payload.current_project_id)


# ---------- projects ----------
@router.get("/projects", response_model=List[schemas.ProjectOut], dependencies=[Depends(require_token)])
async def list_projects(phase: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Project).order_by(models.Project.position, models.Project.name)
    if phase:
        q = q.where(models.Project.phase == phase)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.ProjectOut.model_validate(r) for r in rows]


@router.get("/projects/{project_id}", response_model=schemas.ProjectOut, dependencies=[Depends(require_token)])
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Project).where(models.Project.id == project_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "project not found")
    return schemas.ProjectOut.model_validate(row)


@router.post("/projects", response_model=schemas.ProjectOut, dependencies=[Depends(require_token)])
async def create_project(payload: schemas.ProjectCreate, db: AsyncSession = Depends(get_db)):
    p = models.Project(**payload.model_dump())
    db.add(p)
    db.add(models.Event(actor="ryan", action="project_created", target_type="project", target_id=p.id, payload={"name": p.name}))
    await db.commit()
    await db.refresh(p)
    return schemas.ProjectOut.model_validate(p)


@router.patch("/projects/{project_id}", response_model=schemas.ProjectOut, dependencies=[Depends(require_token)])
async def patch_project(project_id: str, payload: schemas.ProjectPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Project).where(models.Project.id == project_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "project not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="project_updated", target_type="project", target_id=project_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return schemas.ProjectOut.model_validate(row)


# ---------- tasks ----------
@router.get("/tasks", response_model=List[schemas.TaskOut], dependencies=[Depends(require_token)])
async def list_tasks(project_id: Optional[str] = None, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Task).order_by(models.Task.position, models.Task.created_at)
    if project_id:
        q = q.where(models.Task.project_id == project_id)
    if status:
        q = q.where(models.Task.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.TaskOut.model_validate(r) for r in rows]


@router.post("/tasks", response_model=schemas.TaskOut, dependencies=[Depends(require_token)])
async def create_task(payload: schemas.TaskCreate, db: AsyncSession = Depends(get_db)):
    t = models.Task(**payload.model_dump())
    db.add(t)
    db.add(models.Event(actor="ryan", action="task_created", target_type="task", target_id=t.id, payload={"title": t.title, "project_id": t.project_id}))
    await db.commit()
    await db.refresh(t)
    return schemas.TaskOut.model_validate(t)


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut, dependencies=[Depends(require_token)])
async def patch_task(task_id: str, payload: schemas.TaskPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Task).where(models.Task.id == task_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "task not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="task_updated", target_type="task", target_id=task_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return schemas.TaskOut.model_validate(row)


# ---------- decisions ----------
@router.get("/decisions", response_model=List[schemas.DecisionOut], dependencies=[Depends(require_token)])
async def list_decisions(project_id: Optional[str] = None, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Decision).order_by(desc(models.Decision.created_at))
    if project_id:
        q = q.where(models.Decision.project_id == project_id)
    if status:
        q = q.where(models.Decision.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.DecisionOut.model_validate(r) for r in rows]


@router.post("/decisions", response_model=schemas.DecisionOut, dependencies=[Depends(require_token)])
async def create_decision(payload: schemas.DecisionCreate, db: AsyncSession = Depends(get_db)):
    d = models.Decision(**payload.model_dump())
    db.add(d)
    db.add(models.Event(actor="ryan", action="decision_logged", target_type="decision", target_id=d.id, payload={"question": d.question, "project_id": d.project_id}))
    await db.commit()
    await db.refresh(d)
    return schemas.DecisionOut.model_validate(d)


@router.patch("/notes/{note_id}", response_model=schemas.NoteOut, dependencies=[Depends(require_token)])
async def patch_note(note_id: str, payload: schemas.NotePatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Note).where(models.Note.id == note_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "note not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="note_updated", target_type="note", target_id=note_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return schemas.NoteOut.model_validate(row)


@router.patch("/decisions/{decision_id}", response_model=schemas.DecisionOut, dependencies=[Depends(require_token)])
async def patch_decision(decision_id: str, payload: schemas.DecisionPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Decision).where(models.Decision.id == decision_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "decision not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return schemas.DecisionOut.model_validate(row)


# ---------- notes ----------
@router.get("/notes", response_model=List[schemas.NoteOut], dependencies=[Depends(require_token)])
async def list_notes(status: str = "open", target_type: Optional[str] = None, target_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Note).where(models.Note.status == status).order_by(desc(models.Note.created_at))
    if target_type:
        q = q.where(models.Note.target_type == target_type)
    if target_id:
        q = q.where(models.Note.target_id == target_id)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.NoteOut.model_validate(r) for r in rows]


@router.post("/notes", response_model=schemas.NoteOut, dependencies=[Depends(require_token)])
async def create_note(payload: schemas.NoteCreate, db: AsyncSession = Depends(get_db)):
    n = models.Note(**payload.model_dump())
    db.add(n)
    db.add(models.Event(actor="ryan", action="note_added", target_type=n.target_type, target_id=n.target_id, payload={"tag": n.tag}))
    await db.commit()
    await db.refresh(n)
    return schemas.NoteOut.model_validate(n)


@router.post("/notes/{note_id}/resolve", response_model=schemas.NoteOut, dependencies=[Depends(require_token)])
async def resolve_note(note_id: str, payload: schemas.NoteResolve, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone
    row = (await db.execute(select(models.Note).where(models.Note.id == note_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "note not found")
    row.status = "resolved"
    row.resolved_by = payload.resolved_by
    row.resolved_summary = payload.summary
    row.resolved_at = datetime.now(timezone.utc)
    db.add(models.Event(actor=payload.resolved_by, action="note_resolved", target_type="note", target_id=note_id, payload={"summary": payload.summary}))
    await db.commit()
    await db.refresh(row)
    return schemas.NoteOut.model_validate(row)


# ---------- workbench ----------
@router.get("/workbench", response_model=List[schemas.WorkbenchItemOut], dependencies=[Depends(require_token)])
async def list_workbench(project_id: Optional[str] = None, scope: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.WorkbenchItem).order_by(models.WorkbenchItem.position, models.WorkbenchItem.created_at)
    if project_id:
        q = q.where(models.WorkbenchItem.project_id == project_id)
    elif scope == "global":
        q = q.where(models.WorkbenchItem.project_id.is_(None))
    # default (no filter): return ALL items across all projects (for the World view)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.WorkbenchItemOut.model_validate(r) for r in rows]


@router.post("/workbench", response_model=schemas.WorkbenchItemOut, dependencies=[Depends(require_token)])
async def create_workbench(payload: schemas.WorkbenchItemCreate, db: AsyncSession = Depends(get_db)):
    item = models.WorkbenchItem(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return schemas.WorkbenchItemOut.model_validate(item)


# ---------- intel ----------
@router.get("/intel", response_model=List[schemas.IntelOut], dependencies=[Depends(require_token)])
async def list_intel(target_type: Optional[str] = None, target_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.IntelItem).where(models.IntelItem.status == "active").order_by(desc(models.IntelItem.created_at)).limit(20)
    if target_type:
        q = q.where(models.IntelItem.target_type == target_type)
    if target_id:
        q = q.where(models.IntelItem.target_id == target_id)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.IntelOut.model_validate(r) for r in rows]


# ---------- events ----------
@router.get("/events", dependencies=[Depends(require_token)])
async def list_events(limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(models.Event).order_by(desc(models.Event.created_at)).limit(limit)
    )).scalars().all()
    return [{
        "id": e.id,
        "actor": e.actor,
        "action": e.action,
        "target_type": e.target_type,
        "target_id": e.target_id,
        "payload": e.payload,
        "created_at": e.created_at.isoformat(),
    } for e in rows]


# ---------- patterns ----------
@router.get("/patterns", dependencies=[Depends(require_token)])
async def list_patterns(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Pattern).order_by(desc(models.Pattern.candidate_count))
    if status:
        q = q.where(models.Pattern.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "candidate_count": p.candidate_count,
        "created_at": p.created_at.isoformat(),
    } for p in rows]


@router.patch("/workbench/{item_id}", response_model=schemas.WorkbenchItemOut, dependencies=[Depends(require_token)])
async def patch_workbench(item_id: str, payload: schemas.WorkbenchItemPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.WorkbenchItem).where(models.WorkbenchItem.id == item_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "workbench item not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="workbench_updated", target_type="workbench", target_id=item_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return schemas.WorkbenchItemOut.model_validate(row)


@router.patch("/patterns/{pattern_id}", dependencies=[Depends(require_token)])
async def patch_pattern(pattern_id: str, payload: schemas.PatternPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Pattern).where(models.Pattern.id == pattern_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "pattern not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="pattern_updated", target_type="pattern", target_id=pattern_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "name": row.name, "description": row.description, "status": row.status, "candidate_count": row.candidate_count, "created_at": row.created_at.isoformat()}


# ---------- components ----------
@router.get("/components", response_model=List[schemas.ComponentOut], dependencies=[Depends(require_token)])
async def list_components(project_id: Optional[str] = None, kind: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(models.Component).order_by(models.Component.position, models.Component.created_at)
    if project_id:
        q = q.where(models.Component.project_id == project_id)
    if kind:
        q = q.where(models.Component.kind == kind)
    rows = (await db.execute(q)).scalars().all()
    return [schemas.ComponentOut.model_validate(r) for r in rows]


@router.post("/components", response_model=schemas.ComponentOut, dependencies=[Depends(require_token)])
async def create_component(payload: schemas.ComponentCreate, db: AsyncSession = Depends(get_db)):
    c = models.Component(**payload.model_dump())
    db.add(c)
    db.add(models.Event(actor="ryan", action="component_created", target_type="component", target_id=c.id, payload={"name": c.name, "kind": c.kind, "project_id": c.project_id}))
    await db.commit()
    await db.refresh(c)
    return schemas.ComponentOut.model_validate(c)


@router.patch("/components/{component_id}", response_model=schemas.ComponentOut, dependencies=[Depends(require_token)])
async def patch_component(component_id: str, payload: schemas.ComponentPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Component).where(models.Component.id == component_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "component not found")
    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(row, k, v)
    db.add(models.Event(actor="ryan", action="component_updated", target_type="component", target_id=component_id, payload=changes))
    await db.commit()
    await db.refresh(row)
    return schemas.ComponentOut.model_validate(row)


@router.delete("/components/{component_id}", dependencies=[Depends(require_token)])
async def delete_component(component_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(models.Component).where(models.Component.id == component_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "component not found")
    db.add(models.Event(actor="ryan", action="component_deleted", target_type="component", target_id=component_id, payload={"name": row.name}))
    await db.delete(row)
    await db.commit()
    return {"ok": True, "id": component_id}


# ---------- websocket presence ----------
class WSManager:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)


ws_manager = WSManager()


@router.websocket("/ws/presence")
async def ws_presence(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            # echo presence pings back, keepalive
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def listen_pg_notify():
    """Background task: subscribe to atrium_events channel, fan out to WS clients."""
    import asyncpg
    raw_url = settings.database_url.replace("+asyncpg", "")
    while True:
        try:
            conn = await asyncpg.connect(raw_url)
            await conn.add_listener("atrium_events", lambda c, p, ch, payload: asyncio.create_task(ws_manager.broadcast(json.loads(payload))))
            while True:
                await asyncio.sleep(60)
        except Exception as e:
            print(f"pg notify listener error: {e}, reconnecting in 5s")
            await asyncio.sleep(5)
