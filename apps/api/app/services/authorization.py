from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.models.core import (
    ProjectMember,
    Task,
    TaskAssignee,
    TeamMember,
)
from app.models.enums import (
    ProjectRole,
    TeamRole,
)
from app.models.team_project import TeamProject
from app.services.permissions import (
    PermissionContext,
    PermissionScope,
    has_permission,
)


def get_team_role(
    *,
    db: Session,
    team_id: UUID,
    user_id: UUID,
) -> TeamRole | None:
    membership = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )

    if membership is None:
        return None

    return membership.role


def has_team_permission(
    *,
    db: Session,
    current_user: CurrentUser,
    team_id: UUID,
    permission: str,
) -> bool:
    return has_permission(
        db=db,
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        permission=permission,
        ctx=PermissionContext(
            workspace_role=current_user.workspace_role,
            team_role=get_team_role(
                db=db,
                team_id=team_id,
                user_id=current_user.id,
            ),
        ),
        scopes=[
            PermissionScope(
                scope_type="TEAM",
                scope_id=team_id,
            )
        ],
    )


def get_project_role(
    *,
    db: Session,
    project_id: UUID,
    user_id: UUID,
) -> ProjectRole | None:
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id
            == project_id,
            ProjectMember.user_id
            == user_id,
        )
    )

    if membership is None:
        return None

    return membership.role


def get_project_team_role(
    *,
    db: Session,
    project_id: UUID,
    user_id: UUID,
) -> TeamRole | None:
    roles = list(
        db.scalars(
            select(
                TeamMember.role
            )
            .join(
                TeamProject,
                TeamProject.team_id
                == TeamMember.team_id,
            )
            .where(
                TeamProject.project_id
                == project_id,
                TeamMember.user_id
                == user_id,
            )
        )
    )

    if not roles:
        return None

    if TeamRole.MANAGER in roles:
        return TeamRole.MANAGER

    return roles[0]


def build_project_permission_context(
    *,
    db: Session,
    current_user: CurrentUser,
    project_id: UUID,
) -> PermissionContext:
    return PermissionContext(
        workspace_role=current_user.workspace_role,
        team_role=get_project_team_role(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        ),
        project_role=get_project_role(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        ),
    )


def has_global_permission(
    *,
    db: Session,
    current_user: CurrentUser,
    permission: str,
) -> bool:
    return has_permission(
        db=db,
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        permission=permission,
        ctx=PermissionContext(
            workspace_role=current_user.workspace_role
        ),
    )


def has_project_permission(
    *,
    db: Session,
    current_user: CurrentUser,
    project_id: UUID,
    permission: str,
) -> bool:
    ctx = build_project_permission_context(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )

    return has_permission(
        db=db,
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        permission=permission,
        ctx=ctx,
        scopes=[
            PermissionScope(
                scope_type="PROJECT",
                scope_id=project_id,
            )
        ],
    )


def is_task_self_related(
    *,
    db: Session,
    task: Task,
    current_user: CurrentUser,
) -> bool:
    if task.owner_id == current_user.id:
        return True

    assigned = db.scalar(
        select(
            TaskAssignee.id
        ).where(
            TaskAssignee.task_id
            == task.id,
            TaskAssignee.user_id
            == current_user.id,
        )
    )

    return assigned is not None


def has_task_edit_permission(
    *,
    db: Session,
    task: Task,
    current_user: CurrentUser,
) -> bool:
    if (
        task.workspace_id
        != current_user.workspace_id
    ):
        return False

    if task.project_id is not None:
        full_edit = has_project_permission(
            db=db,
            current_user=current_user,
            project_id=task.project_id,
            permission="task.edit",
        )
    else:
        full_edit = has_global_permission(
            db=db,
            current_user=current_user,
            permission="task.edit",
        )

    if full_edit:
        return True

    if not is_task_self_related(
        db=db,
        task=task,
        current_user=current_user,
    ):
        return False

    if task.project_id is not None:
        return has_project_permission(
            db=db,
            current_user=current_user,
            project_id=task.project_id,
            permission="task.edit.self",
        )

    return has_global_permission(
        db=db,
        current_user=current_user,
        permission="task.edit.self",
    )
