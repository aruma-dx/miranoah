from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, exists, or_, select

from app.core.dependencies import CurrentUser
from app.models.core import (
    Project,
    ProjectMember,
    Task,
    TaskAssignee,
)
from app.models.enums import (
    ProjectRole,
    WorkspaceRole,
)


def apply_project_view_scope(
    stmt: Select,
    current_user: CurrentUser,
) -> Select:
    """
    Apply project visibility rules.

    ADMIN:
        All projects in workspace.

    MANAGER:
        Projects they own
        OR projects where ProjectRole is OWNER/MANAGER.

    PLAYER:
        Projects they own
        OR projects where they are a ProjectMember.
    """

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

    membership_exists = exists(
        select(ProjectMember.id).where(
            ProjectMember.project_id
            == Project.id,
            ProjectMember.user_id
            == current_user.id,
        )
    )

    if (
        current_user.workspace_role
        == WorkspaceRole.MANAGER
    ):
        manager_membership_exists = exists(
            select(ProjectMember.id).where(
                ProjectMember.project_id
                == Project.id,
                ProjectMember.user_id
                == current_user.id,
                ProjectMember.role.in_(
                    [
                        ProjectRole.OWNER,
                        ProjectRole.MANAGER,
                    ]
                ),
            )
        )

        return stmt.where(
            or_(
                Project.owner_id
                == current_user.id,

                manager_membership_exists,
            )
        )

    return stmt.where(
        or_(
            Project.owner_id
            == current_user.id,

            membership_exists,
        )
    )


def can_manage_project(
    *,
    project: Project,
    current_user: CurrentUser,
    project_role: ProjectRole | None,
) -> bool:
    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return True

    if (
        project.workspace_id
        != current_user.workspace_id
    ):
        return False

    if project.owner_id == current_user.id:
        return True

    return project_role in {
        ProjectRole.OWNER,
        ProjectRole.MANAGER,
    }


def get_project_role(
    *,
    db,
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


def apply_task_view_scope(
    stmt: Select,
    current_user: CurrentUser,
) -> Select:
    """
    Apply task visibility rules.

    ADMIN:
        All workspace tasks.

    MANAGER:
        Tasks in projects they manage,
        plus tasks directly assigned/requested/owned by them.

    PLAYER:
        Own/requested/assigned tasks,
        plus tasks belonging to projects
        where they are a ProjectMember.
    """

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
            select(TaskAssignee.id).where(
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
        managed_project = exists(
            select(ProjectMember.id).where(
                ProjectMember.project_id
                == Task.project_id,
                ProjectMember.user_id
                == current_user.id,
                ProjectMember.role.in_(
                    [
                        ProjectRole.OWNER,
                        ProjectRole.MANAGER,
                    ]
                ),
            )
        )

        owned_project = exists(
            select(Project.id).where(
                Project.id
                == Task.project_id,
                Project.owner_id
                == current_user.id,
                Project.workspace_id
                == current_user.workspace_id,
            )
        )

        return stmt.where(
            or_(
                directly_related,
                managed_project,
                owned_project,
            )
        )

    member_project = exists(
        select(ProjectMember.id).where(
            ProjectMember.project_id
            == Task.project_id,
            ProjectMember.user_id
            == current_user.id,
        )
    )

    return stmt.where(
        or_(
            directly_related,
            member_project,
        )
    )


def can_edit_task(
    *,
    db,
    task: Task,
    current_user: CurrentUser,
) -> bool:
    """
    ADMIN:
        Any task in workspace.

    MANAGER:
        Tasks in managed projects
        OR directly related tasks.

    PLAYER:
        Only tasks they own or are assigned to.
    """

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

    if task.owner_id == current_user.id:
        return True

    assigned = db.scalar(
        select(TaskAssignee.id).where(
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

    project_role = get_project_role(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
    )

    return can_manage_project(
        project=project,
        current_user=current_user,
        project_role=project_role,
    )
