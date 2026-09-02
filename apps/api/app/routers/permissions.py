from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.db.session import get_db
from app.models.core import (
    PermissionOverride,
    User,
)
from app.models.enums import WorkspaceRole
from app.schemas.permission import (
    PermissionOverrideCreate,
    PermissionOverrideRead,
)


router = APIRouter(
    prefix="/api/v1/permissions",
    tags=["permissions"],
)


ALLOWED_SCOPE_TYPES = {
    "GLOBAL",
    "TEAM",
    "PROJECT",
    "SELF",
    "RELATED",
}


def require_permission_admin(
    current_user: CurrentUser,
) -> None:
    """
    PermissionOverride itself is privilege-escalation capable.

    Therefore its administration must NOT be controlled
    by PermissionOverride.

    Only Workspace Owner / ADMIN may manage overrides.
    """

    if current_user.is_workspace_owner:
        return

    if (
        current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator permission required.",
    )


@router.get(
    "/overrides",
    response_model=list[PermissionOverrideRead],
)
def list_permission_overrides(
    user_id: UUID | None = None,
    scope_type: str | None = None,
    permission_key: str | None = None,
    limit: int = Query(
        default=200,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    require_permission_admin(
        current_user
    )

    stmt = select(
        PermissionOverride
    ).where(
        PermissionOverride.workspace_id
        == current_user.workspace_id
    )

    if user_id is not None:
        stmt = stmt.where(
            PermissionOverride.user_id
            == user_id
        )

    if scope_type is not None:
        normalized_scope_type = (
            scope_type.strip().upper()
        )

        if (
            normalized_scope_type
            not in ALLOWED_SCOPE_TYPES
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid scope_type.",
            )

        stmt = stmt.where(
            PermissionOverride.scope_type
            == normalized_scope_type
        )

    if permission_key is not None:
        stmt = stmt.where(
            PermissionOverride.permission_key
            == permission_key
        )

    stmt = stmt.order_by(
        PermissionOverride.created_at.desc()
    ).limit(limit)

    return list(
        db.scalars(stmt)
    )


@router.post(
    "/overrides",
    response_model=PermissionOverrideRead,
    status_code=status.HTTP_201_CREATED,
)
def create_permission_override(
    data: PermissionOverrideCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    require_permission_admin(
        current_user
    )

    target_user = db.get(
        User,
        data.user_id,
    )

    if (
        target_user is None
        or target_user.workspace_id
        != current_user.workspace_id
    ):
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    scope_type = (
        data.scope_type.strip().upper()
    )

    if (
        scope_type
        not in ALLOWED_SCOPE_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid scope_type.",
        )

    if (
        scope_type
        == "GLOBAL"
        and data.scope_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "GLOBAL scope must not have "
                "scope_id."
            ),
        )

    if (
        scope_type
        in {
            "TEAM",
            "PROJECT",
        }
        and data.scope_id is None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{scope_type} scope requires "
                "scope_id."
            ),
        )

    permission_key = (
        data.permission_key.strip()
    )

    override = PermissionOverride(
        workspace_id=(
            current_user.workspace_id
        ),
        user_id=data.user_id,
        scope_type=scope_type,
        scope_id=data.scope_id,
        permission_key=permission_key,
        effect=data.effect,
    )

    db.add(override)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Permission override already exists."
            ),
        )

    db.refresh(override)

    return override


@router.delete(
    "/overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_permission_override(
    override_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    require_permission_admin(
        current_user
    )

    override = db.scalar(
        select(
            PermissionOverride
        ).where(
            PermissionOverride.id
            == override_id,
            PermissionOverride.workspace_id
            == current_user.workspace_id,
        )
    )

    if override is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Permission override not found."
            ),
        )

    db.delete(override)
    db.commit()

    return None
