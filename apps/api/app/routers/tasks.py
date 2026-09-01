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
    TaskUpdate,
)
from app.services.authorization import (
    has_global_permission,
    has_project_permission,
    has_task_edit_permission,
)
from app.services.scopes import (
    apply_project_view_scope,
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
        get_current_user
    ),
):
    if data.project_id is not None:
        project_stmt = (
            select(Project).where(
                Project.id
                == data.project_id
            )
        )

        project_stmt = (
            apply_project_view_scope(
                stmt=project_stmt,
                current_user=current_user,
            )
        )

        project = db.scalar(
            project_stmt
        )

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

        allowed = (
            has_project_permission(
                db=db,
                current_user=current_user,
                project_id=project.id,
                permission="task.create",
            )
        )

    else:
        allowed = (
            has_global_permission(
                db=db,
                current_user=current_user,
                permission="task.create",
            )
        )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
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

    task = Task(
        workspace_id=(
            current_user.workspace_id
        ),
        **data.model_dump(),
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


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
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

    allowed = (
        has_task_edit_permission(
            db=db,
            task=task,
            current_user=current_user,
        )
    )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    payload = data.model_dump(
        exclude_unset=True
    )

    if (
        "owner_id" in payload
        and payload["owner_id"]
        is not None
    ):
        owner = db.get(
            User,
            payload["owner_id"],
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

    for key, value in payload.items():
        setattr(
            task,
            key,
            value,
        )

    db.commit()
    db.refresh(task)

    return task
