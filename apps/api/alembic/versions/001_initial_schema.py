"""Initial MIRANOAH schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


workspace_role = postgresql.ENUM(
    "ADMIN",
    "MANAGER",
    "PLAYER",
    name="workspacerole",
    create_type=False,
)

team_role = postgresql.ENUM(
    "MANAGER",
    "PLAYER",
    name="teamrole",
    create_type=False,
)

project_role = postgresql.ENUM(
    "OWNER",
    "MANAGER",
    "MEMBER",
    "VIEWER",
    name="projectrole",
    create_type=False,
)

permission_effect = postgresql.ENUM(
    "ALLOW",
    "DENY",
    name="permissioneffect",
    create_type=False,
)

project_status = postgresql.ENUM(
    "PLANNING",
    "ACTIVE",
    "ON_HOLD",
    "BLOCKED",
    "COMPLETED",
    "CANCELLED",
    "ARCHIVED",
    name="projectstatus",
    create_type=False,
)

project_health = postgresql.ENUM(
    "HEALTHY",
    "ATTENTION",
    "AT_RISK",
    "CRITICAL",
    "BLOCKED",
    name="projecthealth",
    create_type=False,
)

task_status = postgresql.ENUM(
    "CANDIDATE",
    "NOT_STARTED",
    "IN_PROGRESS",
    "WAITING_REVIEW",
    "WAITING_INTERNAL",
    "WAITING_EXTERNAL",
    "BLOCKED",
    "ON_HOLD",
    "DONE",
    "CANCELLED",
    name="taskstatus",
    create_type=False,
)

todo_status = postgresql.ENUM(
    "NOT_STARTED",
    "IN_PROGRESS",
    "WAITING",
    "BLOCKED",
    "DONE",
    "SKIPPED",
    name="todostatus",
    create_type=False,
)

priority = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="priority",
    create_type=False,
)

risk_level = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="risklevel",
    create_type=False,
)

deadline_type = postgresql.ENUM(
    "EXPLICIT",
    "RELATIVE",
    "CALENDAR_BASED",
    "AI_INFERRED",
    "MANUAL",
    name="deadlinetype",
    create_type=False,
)

monitoring_policy = postgresql.ENUM(
    "MONITOR_FULL",
    "MONITOR_TASK_ONLY",
    "MONITOR_ON_MENTION",
    "STORE_ONLY",
    "IGNORE",
    name="monitoringpolicy",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    for enum_type in (
        workspace_role,
        team_role,
        project_role,
        permission_effect,
        project_status,
        project_health,
        task_status,
        todo_status,
        priority,
        risk_level,
        deadline_type,
        monitoring_policy,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slack_team_id", sa.String(length=64), nullable=True),
        sa.Column("raw_slack_retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slack_team_id"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_user_id", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("workspace_role", workspace_role, nullable=False),
        sa.Column("is_workspace_owner", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "slack_user_id",
            name="uq_user_workspace_slack",
        ),
    )

    op.create_index(
        op.f("ix_users_workspace_id"),
        "users",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_slack_user_id"),
        "users",
        ["slack_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=False,
    )

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_teams_workspace_id"),
        "teams",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", team_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "user_id",
            name="uq_team_member",
        ),
    )

    op.create_index(
        op.f("ix_team_members_team_id"),
        "team_members",
        ["team_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_team_members_user_id"),
        "team_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", project_status, nullable=False),
        sa.Column("health", project_health, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(length=250), nullable=True),
        sa.Column("slack_primary_channel_id", sa.String(length=64), nullable=True),
        sa.Column("google_calendar_id", sa.String(length=250), nullable=True),
        sa.Column("google_drive_folder_url", sa.Text(), nullable=True),
        sa.Column("notion_page_url", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_projects_workspace_id"),
        "projects",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member",
        ),
    )

    op.create_index(
        op.f("ix_project_members_project_id"),
        "project_members",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_members_user_id"),
        "project_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_milestones_project_id"),
        "milestones",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", priority, nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_type", deadline_type, nullable=True),
        sa.Column("deadline_confidence", sa.Float(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_minutes", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("task_fingerprint", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["milestone_id"],
            ["milestones.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_tasks_workspace_id"),
        "tasks",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_project_id"),
        "tasks",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_status"),
        "tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_due_at"),
        "tasks",
        ["due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_task_fingerprint"),
        "tasks",
        ["task_fingerprint"],
        unique=False,
    )

    op.create_table(
        "task_assignees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "user_id",
            name="uq_task_assignee",
        ),
    )

    op.create_index(
        op.f("ix_task_assignees_task_id"),
        "task_assignees",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_assignees_user_id"),
        "task_assignees",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "todos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", todo_status, nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", priority, nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_todos_task_id"),
        "todos",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "slack_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("monitoring_policy", monitoring_policy, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "slack_channel_id",
            name="uq_workspace_slack_channel",
        ),
    )

    op.create_index(
        op.f("ix_slack_channels_workspace_id"),
        "slack_channels",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "slack_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=64), nullable=False),
        sa.Column("message_ts", sa.String(length=64), nullable=False),
        sa.Column("thread_ts", sa.String(length=64), nullable=True),
        sa.Column("slack_user_id", sa.String(length=64), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_files", sa.Boolean(), nullable=False),
        sa.Column("has_links", sa.Boolean(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "slack_channel_id",
            "message_ts",
            name="uq_slack_message",
        ),
    )

    op.create_index(
        op.f("ix_slack_messages_workspace_id"),
        "slack_messages",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slack_messages_slack_channel_id"),
        "slack_messages",
        ["slack_channel_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slack_messages_message_ts"),
        "slack_messages",
        ["message_ts"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slack_messages_thread_ts"),
        "slack_messages",
        ["thread_ts"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slack_messages_slack_user_id"),
        "slack_messages",
        ["slack_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slack_messages_processed"),
        "slack_messages",
        ["processed"],
        unique=False,
    )

    op.create_table(
        "permission_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("permission_key", sa.String(length=120), nullable=False),
        sa.Column("effect", permission_effect, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_permission_overrides_workspace_id"),
        "permission_overrides",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_overrides_user_id"),
        "permission_overrides",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_overrides_permission_key"),
        "permission_overrides",
        ["permission_key"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(length=120), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("prompt_version", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_audit_logs_workspace_id"),
        "audit_logs",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_action"),
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entity_type"),
        "audit_logs",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entity_id"),
        "audit_logs",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audit_logs_created_at"),
        table_name="audit_logs",
    )
    op.drop_index(
        op.f("ix_audit_logs_entity_id"),
        table_name="audit_logs",
    )
    op.drop_index(
        op.f("ix_audit_logs_entity_type"),
        table_name="audit_logs",
    )
    op.drop_index(
        op.f("ix_audit_logs_action"),
        table_name="audit_logs",
    )
    op.drop_index(
        op.f("ix_audit_logs_workspace_id"),
        table_name="audit_logs",
    )
    op.drop_table("audit_logs")

    op.drop_index(
        op.f("ix_permission_overrides_permission_key"),
        table_name="permission_overrides",
    )
    op.drop_index(
        op.f("ix_permission_overrides_user_id"),
        table_name="permission_overrides",
    )
    op.drop_index(
        op.f("ix_permission_overrides_workspace_id"),
        table_name="permission_overrides",
    )
    op.drop_table("permission_overrides")

    op.drop_index(
        op.f("ix_slack_messages_processed"),
        table_name="slack_messages",
    )
    op.drop_index(
        op.f("ix_slack_messages_slack_user_id"),
        table_name="slack_messages",
    )
    op.drop_index(
        op.f("ix_slack_messages_thread_ts"),
        table_name="slack_messages",
    )
    op.drop_index(
        op.f("ix_slack_messages_message_ts"),
        table_name="slack_messages",
    )
    op.drop_index(
        op.f("ix_slack_messages_slack_channel_id"),
        table_name="slack_messages",
    )
    op.drop_index(
        op.f("ix_slack_messages_workspace_id"),
        table_name="slack_messages",
    )
    op.drop_table("slack_messages")

    op.drop_index(
        op.f("ix_slack_channels_workspace_id"),
        table_name="slack_channels",
    )
    op.drop_table("slack_channels")

    op.drop_index(
        op.f("ix_todos_task_id"),
        table_name="todos",
    )
    op.drop_table("todos")

    op.drop_index(
        op.f("ix_task_assignees_user_id"),
        table_name="task_assignees",
    )
    op.drop_index(
        op.f("ix_task_assignees_task_id"),
        table_name="task_assignees",
    )
    op.drop_table("task_assignees")

    op.drop_index(
        op.f("ix_tasks_task_fingerprint"),
        table_name="tasks",
    )
    op.drop_index(
        op.f("ix_tasks_due_at"),
        table_name="tasks",
    )
    op.drop_index(
        op.f("ix_tasks_status"),
        table_name="tasks",
    )
    op.drop_index(
        op.f("ix_tasks_project_id"),
        table_name="tasks",
    )
    op.drop_index(
        op.f("ix_tasks_workspace_id"),
        table_name="tasks",
    )
    op.drop_table("tasks")

    op.drop_index(
        op.f("ix_milestones_project_id"),
        table_name="milestones",
    )
    op.drop_table("milestones")

    op.drop_index(
        op.f("ix_project_members_user_id"),
        table_name="project_members",
    )
    op.drop_index(
        op.f("ix_project_members_project_id"),
        table_name="project_members",
    )
    op.drop_table("project_members")

    op.drop_index(
        op.f("ix_projects_workspace_id"),
        table_name="projects",
    )
    op.drop_table("projects")

    op.drop_index(
        op.f("ix_team_members_user_id"),
        table_name="team_members",
    )
    op.drop_index(
        op.f("ix_team_members_team_id"),
        table_name="team_members",
    )
    op.drop_table("team_members")

    op.drop_index(
        op.f("ix_teams_workspace_id"),
        table_name="teams",
    )
    op.drop_table("teams")

    op.drop_index(
        op.f("ix_users_email"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_slack_user_id"),
        table_name="users",
    )
    op.drop_index(
        op.f("ix_users_workspace_id"),
        table_name="users",
    )
    op.drop_table("users")

    op.drop_table("workspaces")

    bind = op.get_bind()

    for enum_type in (
        monitoring_policy,
        deadline_type,
        risk_level,
        priority,
        todo_status,
        task_status,
        project_health,
        project_status,
        permission_effect,
        project_role,
        team_role,
        workspace_role,
    ):
        enum_type.drop(bind, checkfirst=True)
