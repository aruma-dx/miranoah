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
    workspace_id = (
        current_user.workspace_id
    )

    now = datetime.now(
        timezone.utc
    )

    closed = [
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    ]

    active_projects = (
        db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.workspace_id
                == workspace_id,
                Project.status
                == ProjectStatus.ACTIVE,
            )
        )
        or 0
    )

    open_tasks = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.workspace_id
                == workspace_id,
                Task.status.notin_(
                    closed
                ),
                Task.deleted_at.is_(None),
            )
        )
        or 0
    )

    overdue = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.workspace_id
                == workspace_id,
                Task.status.notin_(
                    closed
                ),
                Task.due_at < now,
                Task.deleted_at.is_(None),
            )
        )
        or 0
    )

    high_risk = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.workspace_id
                == workspace_id,
                Task.risk_level.in_(
                    [
                        RiskLevel.HIGH,
                        RiskLevel.CRITICAL,
                    ]
                ),
                Task.deleted_at.is_(None),
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
