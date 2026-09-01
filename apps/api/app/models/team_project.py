from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import TimestampMixin, uuid_pk


class TeamProject(Base, TimestampMixin):
    __tablename__ = "team_projects"

    id: Mapped[uuid.UUID] = uuid_pk()

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "teams.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "project_id",
            name="uq_team_project",
        ),
    )
