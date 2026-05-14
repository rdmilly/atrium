from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    name: str
    glyph_color: str = "#7A6F62"
    phase: str = "active"
    vision: str = ""
    journal: str = ""
    template: str = "software"
    public: bool = False
    slug: Optional[str] = None
    public_summary: str = ""
    progress: int = 0
    position: int = 0


class ProjectCreate(ProjectBase):
    pass


class ProjectPatch(BaseModel):
    name: Optional[str] = None
    glyph_color: Optional[str] = None
    phase: Optional[str] = None
    vision: Optional[str] = None
    journal: Optional[str] = None
    template: Optional[str] = None
    public: Optional[bool] = None
    slug: Optional[str] = None
    public_summary: Optional[str] = None
    progress: Optional[int] = None
    position: Optional[int] = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class TaskBase(BaseModel):
    project_id: str
    title: str
    status: str = "next"
    effort: Optional[str] = None
    position: int = 0


class TaskCreate(TaskBase):
    pass


class TaskPatch(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    effort: Optional[str] = None
    position: Optional[int] = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class DecisionCreate(BaseModel):
    project_id: str
    question: str
    options: List[Dict[str, Any]] = []
    choice: Optional[str] = None
    reasoning: Optional[str] = None


class DecisionPatch(BaseModel):
    question: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    choice: Optional[str] = None
    reasoning: Optional[str] = None
    status: Optional[str] = None
    public: Optional[bool] = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    question: str
    options: List[Dict[str, Any]] = []
    choice: Optional[str] = None
    reasoning: Optional[str] = None
    status: str
    public: bool = False
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    target_type: str
    target_id: str
    body: str
    tag: str = "@me"


class NoteResolve(BaseModel):
    summary: str
    resolved_by: str = "claude"


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    target_type: str
    target_id: str
    body: str
    tag: str
    status: str
    resolved_by: Optional[str] = None
    resolved_summary: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class WorkbenchItemCreate(BaseModel):
    project_id: Optional[str] = None
    section: str
    body: str
    tag: Optional[str] = None
    position: int = 0


class WorkbenchItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: Optional[str] = None
    section: str
    body: str
    tag: Optional[str] = None
    position: int
    created_at: datetime
    updated_at: datetime


class IntelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source: str
    body: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    severity: str
    status: str
    created_at: datetime


class FocusOut(BaseModel):
    current_project_id: Optional[str] = None


class FocusSet(BaseModel):
    current_project_id: Optional[str] = None


class SessionInitOut(BaseModel):
    focus: FocusOut
    open_notes: List[NoteOut]
    recent_events: List[Dict[str, Any]]
    recent_decisions: List[DecisionOut]



class WorkbenchItemPatch(BaseModel):
    section: Optional[str] = None
    body: Optional[str] = None
    tag: Optional[str] = None
    position: Optional[int] = None
    project_id: Optional[str] = None


class PatternPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class NotePatch(BaseModel):
    body: Optional[str] = None
    tag: Optional[str] = None
    public: Optional[bool] = None


class ComponentBase(BaseModel):
    project_id: str
    name: str
    kind: str
    status: str = "planned"
    description: str = ""
    location: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    public: bool = False
    position: int = 0


class ComponentCreate(ComponentBase):
    pass


class ComponentPatch(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    public: Optional[bool] = None
    position: Optional[int] = None


class ComponentOut(ComponentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
