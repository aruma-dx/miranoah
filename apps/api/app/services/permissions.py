from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    PermissionEffect,
    PermissionOverride,
)
from app.models.enums import (
    ProjectRole,
    TeamRole,
    WorkspaceRole,
)


SCOPE_GLOBAL = "GLOBAL"
SCOPE_TEAM = "TEAM"
SCOPE_PROJECT = "PROJECT"
SCOPE_SELF = "SELF"
SCOPE_RELATED = "RELATED"


ROLE_DEFAULTS: dict[
    WorkspaceRole,
    set[str],
] = {
    WorkspaceRole.ADMIN: {
        "*",
    },

    WorkspaceRole.MANAGER: {
        "project.view",
        "project.create",
        "project.edit",

        "task.view",
        "task.create",
        "task.edit",
        "task.assign",

        "todo.view",
        "todo.edit",

        "risk.view",
        "risk.edit",

        "blocker.view",
        "blocker.edit",

        "workload.view",

        "ai_review.view",
        "ai_review.approve",

        "member.view",
    },

    WorkspaceRole.PLAYER: {
        "project.view",

        "task.view",
        "task.edit.self",

        "todo.view",
        "todo.edit.self",

        "blocker.create",
    },
}


TEAM_MANAGER_PERMISSIONS = {
    "project.view",
    "project.create",
    "project.edit",

    "task.view",
    "task.create",
    "task.edit",
    "task.assign",

    "todo.view",
    "todo.edit",

    "risk.view",
    "risk.edit",

    "blocker.view",
    "blocker.edit",

    "workload.view",

    "ai_review.view",
    "ai_review.approve",

    "member.view",
}


PROJECT_MANAGER_PERMISSIONS = {
    "project.view",
    "project.edit",

    "task.view",
    "task.create",
    "task.edit",
    "task.assign",

    "todo.view",
    "todo.edit",

    "risk.view",
    "risk.edit",

    "blocker.view",
    "blocker.edit",

    "ai_review.view",
    "ai_review.approve",
}


PROJECT_MEMBER_PERMISSIONS = {
    "project.view",
    "task.view",
    "todo.view",
}


@dataclass(frozen=True)
class PermissionContext:
    workspace_role: WorkspaceRole

    team_role: TeamRole | None = None
    project_role: ProjectRole | None = None


@dataclass(frozen=True)
class PermissionScope:
    scope_type: str
    scope_id: UUID | None = None


def _role_default_allows(
    permission: str,
    ctx: PermissionContext,
) -> bool:
    if (
        ctx.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return True

    workspace_defaults = ROLE_DEFAULTS.get(
        ctx.workspace_role,
        set(),
    )

    if (
        permission in workspace_defaults
        or "*" in workspace_defaults
    ):
        return True

    if (
        ctx.team_role
        == TeamRole.MANAGER
        and permission
        in TEAM_MANAGER_PERMISSIONS
    ):
        return True

    if (
        ctx.project_role
        in {
            ProjectRole.OWNER,
            ProjectRole.MANAGER,
        }
        and permission
        in PROJECT_MANAGER_PERMISSIONS
    ):
        return True

    if (
        ctx.project_role
        in {
            ProjectRole.MEMBER,
            ProjectRole.VIEWER,
        }
        and permission
        in PROJECT_MEMBER_PERMISSIONS
    ):
        return True

    return False


def _load_matching_overrides(
    *,
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    permission: str,
    scopes: list[PermissionScope],
) -> list[PermissionOverride]:
    if not scopes:
        scopes = [
            PermissionScope(
                scope_type=SCOPE_GLOBAL,
                scope_id=None,
            )
        ]

    conditions = []

    from sqlalchemy import and_, or_

    for scope in scopes:
        if scope.scope_id is None:
            conditions.append(
                and_(
                    PermissionOverride.scope_type
                    == scope.scope_type,
                    PermissionOverride.scope_id.is_(
                        None
                    ),
                )
            )
        else:
            conditions.append(
                and_(
                    PermissionOverride.scope_type
                    == scope.scope_type,
                    PermissionOverride.scope_id
                    == scope.scope_id,
                )
            )

    stmt = select(
        PermissionOverride
    ).where(
        PermissionOverride.workspace_id
        == workspace_id,
        PermissionOverride.user_id
        == user_id,
        PermissionOverride.permission_key.in_(
            [
                permission,
                "*",
            ]
        ),
        or_(*conditions),
    )

    return list(
        db.scalars(stmt)
    )


def has_permission(
    *,
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    permission: str,
    ctx: PermissionContext,
    scopes: list[PermissionScope]
    | None = None,
) -> bool:
    """
    Effective permission precedence:

    1. Explicit DENY
    2. Explicit ALLOW
    3. Role defaults
    4. DENY
    """

    effective_scopes = [
        PermissionScope(
            scope_type=SCOPE_GLOBAL,
            scope_id=None,
        )
    ]

    if scopes:
        effective_scopes.extend(
            scopes
        )

    overrides = (
        _load_matching_overrides(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            permission=permission,
            scopes=effective_scopes,
        )
    )

    # 1. Explicit DENY always wins.
    for override in overrides:
        if (
            override.effect
            == PermissionEffect.DENY
        ):
            return False

    # 2. Explicit ALLOW.
    for override in overrides:
        if (
            override.effect
            == PermissionEffect.ALLOW
        ):
            return True

    # 3. Role default.
    if _role_default_allows(
        permission=permission,
        ctx=ctx,
    ):
        return True

    # 4. Default deny.
    return False
