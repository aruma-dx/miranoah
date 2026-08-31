from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.enums import Priority, ProjectHealth, ProjectStatus


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=250)
    description: str | None = None
    priority: Priority = Priority.MEDIUM
    owner_id: UUID | None = None
    start_at: datetime | None = None
    due_at: datetime | None = None
    client_name: str | None = None


class ProjectRead(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: ProjectStatus
    health: ProjectHealth
    priority: Priority
    owner_id: UUID | None
    progress: int
    start_at: datetime | None
    due_at: datetime | None
    client_name: str | None

    model_config = {"from_attributes": True}
