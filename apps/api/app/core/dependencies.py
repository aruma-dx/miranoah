from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    SESSION_COOKIE_NAME,
    decode_session_token,
)
from app.db.session import get_db
from app.models.core import User
from app.models.enums import WorkspaceRole


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    workspace_id: UUID
    slack_user_id: str | None
    email: str | None
    display_name: str
    workspace_role: WorkspaceRole
    is_workspace_owner: bool
    is_active: bool


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUser:
    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    payload = decode_session_token(
        token
    )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session user.",
        )

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active.",
        )

    return CurrentUser(
        id=user.id,
        workspace_id=user.workspace_id,
        slack_user_id=user.slack_user_id,
        email=user.email,
        display_name=user.display_name,
        workspace_role=user.workspace_role,
        is_workspace_owner=user.is_workspace_owner,
        is_active=user.is_active,
    )


def require_workspace_roles(
    *allowed_roles: WorkspaceRole,
):
    def dependency(
        current_user: CurrentUser = Depends(
            get_current_user
        ),
    ) -> CurrentUser:
        if (
            current_user.is_workspace_owner
            or current_user.workspace_role
            == WorkspaceRole.ADMIN
        ):
            return current_user

        if (
            current_user.workspace_role
            not in allowed_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission.",
            )

        return current_user

    return dependency


require_admin = require_workspace_roles(
    WorkspaceRole.ADMIN
)

require_manager = require_workspace_roles(
    WorkspaceRole.MANAGER
)

require_manager_or_admin = (
    require_workspace_roles(
        WorkspaceRole.ADMIN,
        WorkspaceRole.MANAGER,
    )
)

require_authenticated = get_current_user
