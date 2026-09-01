"""Add team-project relationships.

Revision ID: 002_team_projects
Revises: 001_initial_schema
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "002_team_projects"
down_revision: str | None = "001_initial_schema"

branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "team_projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "project_id",
            name="uq_team_project",
        ),
    )

    op.create_index(
        op.f(
            "ix_team_projects_team_id"
        ),
        "team_projects",
        ["team_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_team_projects_project_id"
        ),
        "team_projects",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_team_projects_project_id"
        ),
        table_name="team_projects",
    )

    op.drop_index(
        op.f(
            "ix_team_projects_team_id"
        ),
        table_name="team_projects",
    )

    op.drop_table(
        "team_projects"
    )
