"""Add permission override uniqueness indexes.

Revision ID: 003_permission_override_indexes
Revises: 002_team_projects
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op


revision: str = "003_permission_override_indexes"
down_revision: str | None = "002_team_projects"

branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # scope_idあり
    op.create_index(
        "uq_permission_override_scoped",
        "permission_overrides",
        [
            "workspace_id",
            "user_id",
            "scope_type",
            "scope_id",
            "permission_key",
        ],
        unique=True,
        postgresql_where=(
            "scope_id IS NOT NULL"
        ),
    )

    # GLOBAL等 scope_idなし
    # PostgreSQLではNULL同士は通常重複扱いにならないため、
    # scope_id IS NULL専用のUnique Indexを別に作る。
    op.create_index(
        "uq_permission_override_unscoped",
        "permission_overrides",
        [
            "workspace_id",
            "user_id",
            "scope_type",
            "permission_key",
        ],
        unique=True,
        postgresql_where=(
            "scope_id IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_permission_override_unscoped",
        table_name="permission_overrides",
    )

    op.drop_index(
        "uq_permission_override_scoped",
        table_name="permission_overrides",
    )
