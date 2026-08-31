from dataclasses import dataclass
from app.models.enums import ProjectRole, TeamRole, WorkspaceRole


ROLE_DEFAULTS: dict[WorkspaceRole, set[str]] = {
    WorkspaceRole.ADMIN: {"*"},
    WorkspaceRole.MANAGER: {
        "project.view", "project.edit", "task.view", "task.create", "task.edit", "task.assign",
        "todo.view", "todo.edit", "risk.view", "risk.edit", "blocker.view", "blocker.edit",
        "workload.view", "ai_review.view", "ai_review.approve", "member.view",
    },
    WorkspaceRole.PLAYER: {
        "project.view", "task.view", "task.edit.self", "todo.view", "todo.edit.self", "blocker.create",
    },
}


@dataclass(frozen=True)
class PermissionContext:
    workspace_role: WorkspaceRole
    team_role: TeamRole | None = None
    project_role: ProjectRole | None = None
    explicit_allow: frozenset[str] = frozenset()
    explicit_deny: frozenset[str] = frozenset()


def has_permission(permission: str, ctx: PermissionContext) -> bool:
    # Explicit DENY always wins.
    if permission in ctx.explicit_deny or "*" in ctx.explicit_deny:
        return False
    if permission in ctx.explicit_allow or "*" in ctx.explicit_allow:
        return True
    if ctx.workspace_role == WorkspaceRole.ADMIN:
        return True

    defaults = ROLE_DEFAULTS.get(ctx.workspace_role, set())
    if permission in defaults:
        return True

    if ctx.team_role == TeamRole.MANAGER and permission in {
        "project.view", "project.edit", "task.view", "task.create", "task.edit", "task.assign",
        "todo.view", "todo.edit", "risk.view", "risk.edit", "blocker.view", "blocker.edit",
        "workload.view", "ai_review.view", "ai_review.approve", "member.view",
    }:
        return True

    if ctx.project_role in {ProjectRole.OWNER, ProjectRole.MANAGER} and permission in {
        "project.view", "project.edit", "task.view", "task.create", "task.edit", "task.assign",
        "todo.view", "todo.edit", "risk.view", "risk.edit", "blocker.view", "blocker.edit",
        "ai_review.view", "ai_review.approve",
    }:
        return True

    if ctx.project_role in {ProjectRole.MEMBER, ProjectRole.VIEWER} and permission in {"project.view", "task.view", "todo.view"}:
        return True

    return False
