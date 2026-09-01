from datetime import (
    datetime,
    timezone,
)

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.db.session import get_db
from app.models.core import (
    Project,
    Task,
)
from app.models.enums import (
    ProjectStatus,
    RiskLevel,
    TaskStatus,
)
from app.services.scopes import (
    apply_project_view_scope,
    apply_task_view_scope,
)


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
)


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    now = datetime.now(
        timezone.utc
    )

    closed = [
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    ]

    project_stmt = select(
        func.count()
    ).select_from(Project)

    project_stmt = (
        apply_project_view_scope(
            stmt=project_stmt,
            current_user=current_user,
        )
    )

    project_stmt = project_stmt.where(
        Project.status
        == ProjectStatus.ACTIVE
    )

    active_projects = (
        db.scalar(project_stmt)
        or 0
    )

    task_base = select(
        Task.id
    )

    task_base = apply_task_view_scope(
        stmt=task_base,
        current_user=current_user,
    )

    visible_task_ids = (
        task_base.subquery()
    )

    open_tasks = (
        db.scalar(
            select(func.count())
            .select_from(
                visible_task_ids
            )
            .join(
                Task,
                Task.id
                == visible_task_ids.c.id,
            )
            .where(
                Task.status.notin_(
                    closed
                )
            )
        )
        or 0
    )

    overdue = (
        db.scalar(
            select(func.count())
            .select_from(
                visible_task_ids
            )
            .join(
                Task,
                Task.id
                == visible_task_ids.c.id,
            )
            .where(
                Task.status.notin_(
                    closed
                ),
                Task.due_at < now,
            )
        )
        or 0
    )

    high_risk = (
        db.scalar(
            select(func.count())
            .select_from(
                visible_task_ids
            )
            .join(
                Task,
                Task.id
                == visible_task_ids.c.id,
            )
            .where(
                Task.risk_level.in_(
                    [
                        RiskLevel.HIGH,
                        RiskLevel.CRITICAL,
                    ]
                )
            )
        )
        or 0
    )

    return {
        "active_projects": (
            active_projects
        ),
        "open_tasks": open_tasks,
        "overdue": overdue,
        "high_risk": high_risk,
    }
