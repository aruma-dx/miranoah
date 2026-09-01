from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, exists, or_, select

from app.core.dependencies import CurrentUser
from app.models.core import (
    Project,
    ProjectMember,
    Task,
    TaskAssignee,
    TeamMember,
)
from app.models.enums import (
    ProjectRole,
    TeamRole,
    WorkspaceRole,
)
from app.models.team_project import TeamProject


def _project_member_exists(
    *,
    project_id,
    user_id,
):
    return exists(
        select(
            ProjectMember.id
        ).where(
            ProjectMember.project_id
            == project_id,
            ProjectMember.user_id
            == user_id,
        )
    )


def _project_manager_exists(
    *,
    project_id,
    user_id,
):
    return exists(
        select(
            ProjectMember.id
        ).where(
            ProjectMember.project_id
            == project_id,
            ProjectMember.user_id
            == user_id,
            ProjectMember.role.in_(
                [
                    ProjectRole.OWNER,
                    ProjectRole.MANAGER,
                ]
            ),
        )
    )


def _team_project_member_exists(
    *,
    project_id,
    user_id,
):
    return exists(
        select(
            TeamProject.id
        )
        .join(
            TeamMember,
            TeamMember.team_id
            == TeamProject.team_id,
        )
        .where(
            TeamProject.project_id
            == project_id,
            TeamMember.user_id
            == user_id,
        )
    )


def _team_project_manager_exists(
    *,
    project_id,
    user_id,
):
    return exists(
        select(
            TeamProject.id
        )
        .join(
            TeamMember,
            TeamMember.team_id
            == TeamProject.team_id,
        )
        .where(
            TeamProject.project_id
            == project_id,
            TeamMember.user_id
            == user_id,
            TeamMember.role
            == TeamRole.MANAGER,
        )
    )


def apply_project_view_scope(
    stmt: Select,
    current_user: CurrentUser,
) -> Select:
    stmt = stmt.where(
        Project.workspace_id
        == current_user.workspace_id
    )

    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return stmt

    if (
        current_user.workspace_role
        == WorkspaceRole.MANAGER
    ):
        return stmt.where(
            or_(
                Project.owner_id
                == current_user.id,

                _project_manager_exists(
                    project_id=Project.id,
                    user_id=current_user.id,
                ),

                _team_project_manager_exists(
                    project_id=Project.id,
                    user_id=current_user.id,
                ),
            )
        )

    return stmt.where(
        or_(
            Project.owner_id
            == current_user.id,

            _project_member_exists(
                project_id=Project.id,
                user_id=current_user.id,
            ),

            _team_project_member_exists(
                project_id=Project.id,
                user_id=current_user.id,
            ),
        )
    )


def get_project_role(
    *,
    db,
    project_id: UUID,
    user_id: UUID,
) -> ProjectRole | None:
    membership = db.scalar(
        select(
            ProjectMember
        ).where(
            ProjectMember.project_id
            == project_id,
            ProjectMember.user_id
            == user_id,
        )
    )

    if membership is None:
        return None

    return membership.role


def is_team_project_manager(
    *,
    db,
    project_id: UUID,
    user_id: UUID,
) -> bool:
    result = db.scalar(
        select(
            TeamProject.id
        )
        .join(
            TeamMember,
            TeamMember.team_id
            == TeamProject.team_id,
        )
        .where(
            TeamProject.project_id
            == project_id,
            TeamMember.user_id
            == user_id,
            TeamMember.role
            == TeamRole.MANAGER,
        )
        .limit(1)
    )

    return result is not None


def can_manage_project(
    *,
    db,
    project: Project,
    current_user: CurrentUser,
) -> bool:
    if (
        project.workspace_id
        != current_user.workspace_id
    ):
        return False

    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return True

    if (
        project.owner_id
        == current_user.id
    ):
        return True

    project_role = get_project_role(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
    )

    if project_role in {
        ProjectRole.OWNER,
        ProjectRole.MANAGER,
    }:
        return True

    if (
        current_user.workspace_role
        == WorkspaceRole.MANAGER
        and is_team_project_manager(
            db=db,
            project_id=project.id,
            user_id=current_user.id,
        )
    ):
        return True

    return False


def apply_task_view_scope(
    stmt: Select,
    current_user: CurrentUser,
) -> Select:
    stmt = stmt.where(
        Task.workspace_id
        == current_user.workspace_id,
        Task.deleted_at.is_(None),
    )

    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return stmt

    directly_related = or_(
        Task.owner_id
        == current_user.id,

        Task.requester_id
        == current_user.id,

        exists(
            select(
                TaskAssignee.id
            ).where(
                TaskAssignee.task_id
                == Task.id,
                TaskAssignee.user_id
                == current_user.id,
            )
        ),
    )

    if (
        current_user.workspace_role
        == WorkspaceRole.MANAGER
    ):
        return stmt.where(
            or_(
                directly_related,

                _project_manager_exists(
                    project_id=Task.project_id,
                    user_id=current_user.id,
                ),

                _team_project_manager_exists(
                    project_id=Task.project_id,
                    user_id=current_user.id,
                ),

                exists(
                    select(
                        Project.id
                    ).where(
                        Project.id
                        == Task.project_id,
                        Project.owner_id
                        == current_user.id,
                        Project.workspace_id
                        == current_user.workspace_id,
                    )
                ),
            )
        )

    return stmt.where(
        or_(
            directly_related,

            _project_member_exists(
                project_id=Task.project_id,
                user_id=current_user.id,
            ),

            _team_project_member_exists(
                project_id=Task.project_id,
                user_id=current_user.id,
            ),
        )
    )


def can_edit_task(
    *,
    db,
    task: Task,
    current_user: CurrentUser,
) -> bool:
    if (
        task.workspace_id
        != current_user.workspace_id
    ):
        return False

    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return True

    if (
        task.owner_id
        == current_user.id
    ):
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

    if assigned is not None:
        return True

    if (
        current_user.workspace_role
        != WorkspaceRole.MANAGER
    ):
        return False

    if task.project_id is None:
        return (
            task.requester_id
            == current_user.id
        )

    project = db.get(
        Project,
        task.project_id,
    )

    if project is None:
        return False

    return can_manage_project(
        db=db,
        project=project,
        current_user=current_user,
    )
