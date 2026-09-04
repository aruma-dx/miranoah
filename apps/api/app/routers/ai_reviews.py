from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.db.session import get_db
from app.models.core import Task
from app.models.enums import TaskStatus
from app.schemas.task import TaskRead
from app.services.authorization import (
    has_global_permission,
    has_project_permission,
)
from app.services.scopes import (
    apply_task_view_scope,
)


router = APIRouter(
    prefix="/api/v1/ai-reviews",
    tags=["ai-reviews"],
)


def _can_view_review(
    *,
    db: Session,
    current_user: CurrentUser,
    task: Task,
) -> bool:
    if task.project_id is not None:
        return has_project_permission(
            db=db,
            current_user=current_user,
            project_id=task.project_id,
            permission="ai_review.view",
        )

    return has_global_permission(
        db=db,
        current_user=current_user,
        permission="ai_review.view",
    )


def _can_approve_review(
    *,
    db: Session,
    current_user: CurrentUser,
    task: Task,
) -> bool:
    if task.project_id is not None:
        return has_project_permission(
            db=db,
            current_user=current_user,
            project_id=task.project_id,
            permission="ai_review.approve",
        )

    return has_global_permission(
        db=db,
        current_user=current_user,
        permission="ai_review.approve",
    )


def _get_candidate(
    *,
    db: Session,
    current_user: CurrentUser,
    task_id: UUID,
) -> Task:
    stmt = select(Task).where(
        Task.id == task_id,
        Task.status == TaskStatus.CANDIDATE,
        Task.ai_generated.is_(True),
    )

    stmt = apply_task_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    task = db.scalar(stmt)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="AI review candidate not found.",
        )

    return task


@router.get(
    "",
    response_model=list[TaskRead],
)
def list_ai_reviews(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = (
        select(Task)
        .where(
            Task.status
            == TaskStatus.CANDIDATE,
            Task.ai_generated.is_(True),
        )
        .order_by(
            Task.created_at.desc()
        )
    )

    stmt = apply_task_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    tasks = list(
        db.scalars(stmt)
    )

    return [
        task
        for task in tasks
        if _can_view_review(
            db=db,
            current_user=current_user,
            task=task,
        )
    ]


@router.post(
    "/{task_id}/approve",
    response_model=TaskRead,
)
def approve_ai_review(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    task = _get_candidate(
        db=db,
        current_user=current_user,
        task_id=task_id,
    )

    if not _can_approve_review(
        db=db,
        current_user=current_user,
        task=task,
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    task.status = (
        TaskStatus.NOT_STARTED
    )

    db.commit()
    db.refresh(task)

    return task


@router.post(
    "/{task_id}/reject",
    response_model=TaskRead,
)
def reject_ai_review(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    task = _get_candidate(
        db=db,
        current_user=current_user,
        task_id=task_id,
    )

    if not _can_approve_review(
        db=db,
        current_user=current_user,
        task=task,
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    task.status = (
        TaskStatus.CANCELLED
    )

    db.commit()
    db.refresh(task)

    return task
