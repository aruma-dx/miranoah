from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    require_manager_or_admin,
)
from app.db.session import get_db
from app.models.core import (
    Project,
    Task,
    User,
)
from app.models.enums import (
    TaskStatus,
)
from app.schemas.task import (
    TaskCreate,
    TaskRead,
)
from app.services.scopes import (
    apply_task_view_scope,
)


router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"],
)


@router.get(
    "",
    response_model=list[TaskRead],
)
def list_tasks(
    project_id: UUID | None = None,
    status: TaskStatus | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = select(Task)

    stmt = apply_task_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    if project_id is not None:
        stmt = stmt.where(
            Task.project_id
            == project_id
        )

    if status is not None:
        stmt = stmt.where(
            Task.status
            == status
        )

    stmt = (
        stmt
        .order_by(
            Task.due_at.asc().nullslast(),
            Task.created_at.desc(),
        )
        .limit(limit)
    )

    return list(
        db.scalars(stmt)
    )


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_manager_or_admin
    ),
):
    if data.project_id is not None:
        project = db.get(
            Project,
            data.project_id,
        )

        if (
            project is None
            or project.workspace_id
            != current_user.workspace_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

    if data.requester_id is not None:
        requester = db.get(
            User,
            data.requester_id,
        )

        if (
            requester is None
            or requester.workspace_id
            != current_user.workspace_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid requester.",
            )

    if data.owner_id is not None:
        owner = db.get(
            User,
            data.owner_id,
        )

        if (
            owner is None
            or owner.workspace_id
            != current_user.workspace_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid owner.",
            )

    payload = data.model_dump()

    task = Task(
        workspace_id=(
            current_user.workspace_id
        ),
        **payload,
        status=TaskStatus.NOT_STARTED,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get(
    "/{task_id}",
    response_model=TaskRead,
)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = select(Task).where(
        Task.id == task_id
    )

    stmt = apply_task_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    task = db.scalar(stmt)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task
