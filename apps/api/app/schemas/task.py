from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.enums import DeadlineType, Priority, RiskLevel, TaskStatus


class TaskCreate(BaseModel):
    workspace_id: UUID
    project_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    requester_id: UUID | None = None
    owner_id: UUID | None = None
    priority: Priority = Priority.MEDIUM
    due_at: datetime | None = None
    deadline_type: DeadlineType | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    ai_generated: bool = False
    ai_confidence: float | None = Field(default=None, ge=0, le=1)


class TaskRead(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    requester_id: UUID | None
    owner_id: UUID | None
    due_at: datetime | None
    deadline_type: DeadlineType | None
    deadline_confidence: float | None
    progress: int
    risk_level: RiskLevel
    ai_generated: bool
    ai_confidence: float | None

    model_config = {"from_attributes": True}
