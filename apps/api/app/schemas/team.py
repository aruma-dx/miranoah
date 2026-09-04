from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TeamRole


class TeamCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None


class TeamRead(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None

    model_config = {
        "from_attributes": True,
    }


class TeamMemberCreate(BaseModel):
    user_id: UUID
    role: TeamRole = TeamRole.PLAYER


class TeamMemberRead(BaseModel):
    id: UUID
    team_id: UUID
    user_id: UUID
    role: TeamRole

    model_config = {
        "from_attributes": True,
    }
