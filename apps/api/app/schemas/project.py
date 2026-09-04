from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    Priority,
    ProjectHealth,
    ProjectRole,
    ProjectStatus,
)


class ProjectCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=250,
    )

    description: str | None = None
    priority: Priority = Priority.MEDIUM
    owner_id: UUID | None = None
    start_at: datetime | None = None
    due_at: datetime | None = None
    client_name: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    description: str | None = None
    status: ProjectStatus | None = None
    health: ProjectHealth | None = None
    priority: Priority | None = None
    owner_id: UUID | None = None

    progress: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

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

    model_config = {
        "from_attributes": True,
    }


class ProjectMemberCreate(BaseModel):
    user_id: UUID
    role: ProjectRole = ProjectRole.MEMBER


class ProjectMemberRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    role: ProjectRole

    model_config = {
        "from_attributes": True,
    }
