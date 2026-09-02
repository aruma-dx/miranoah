from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.core import PermissionEffect


class PermissionOverrideCreate(BaseModel):
    user_id: UUID

    scope_type: str = Field(
        min_length=1,
        max_length=30,
    )

    scope_id: UUID | None = None

    permission_key: str = Field(
        min_length=1,
        max_length=120,
    )

    effect: PermissionEffect


class PermissionOverrideRead(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID

    scope_type: str
    scope_id: UUID | None

    permission_key: str
    effect: PermissionEffect

    model_config = {
        "from_attributes": True,
    }
