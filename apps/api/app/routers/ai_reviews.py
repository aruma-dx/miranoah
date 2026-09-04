from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel
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
)
from app.models.enums import (
    DeadlineType,
    Priority,
    TaskStatus,
)
from app.schemas.task import TaskRead
from app.services.authorization import (
    has_global_permission,
    has_project_permission,
)
from app.services.scopes import (
    apply_project_view_scope,
    apply_task_view_scope,
)


router = APIRouter(
    prefix="/api/v1/ai-reviews",
    tags=["ai-reviews"],
)


class AIReviewApproveRequest(
    BaseModel
):
    title: str
    description: str | None = None

    project_id: UUID | None = None

    priority: Priority = (
        Priority.MEDIUM
    )

    due_at: datetime | None = None


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


def _can_approve_target_project(
    *,
    db: Session,
    current_user: CurrentUser,
    project_id: UUID | None,
) -> bool:
    if project_id is None:
        return has_global_permission(
            db=db,
            current_user=current_user,
            permission="ai_review.approve",
        )

    return has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project_id,
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
        Task.status
        == TaskStatus.CANDIDATE,
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
            detail=(
                "AI review candidate "
                "not found."
            ),
        )

    return task


def _validate_project(
    *,
    db: Session,
    current_user: CurrentUser,
    project_id: UUID | None,
) -> Project | None:
    if project_id is None:
        return None

    stmt = select(
        Project
    ).where(
        Project.id == project_id
    )

    stmt = apply_project_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    project = db.scalar(stmt)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return project


@router.get(
    "",
    response_model=list[TaskRead],
)
def list_ai_reviews(
    db: Session = Depends(
        get_db
    ),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = (
        select(Task)
        .where(
            Task.status
            == TaskStatus.CANDIDATE,
            Task.ai_generated.is_(
                True
            ),
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
    data: (
        AIReviewApproveRequest
        | None
    ) = None,
    db: Session = Depends(
        get_db
    ),
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
            detail=(
                "Insufficient permission."
            ),
        )

    if data is not None:
        title = (
            data.title
            .strip()
        )

        if not title:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Task title is required."
                ),
            )

        _validate_project(
            db=db,
            current_user=current_user,
            project_id=(
                data.project_id
            ),
        )

        if not (
            _can_approve_target_project(
                db=db,
                current_user=current_user,
                project_id=(
                    data.project_id
                ),
            )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Insufficient permission "
                    "for target Project."
                ),
            )

        task.title = title

        task.description = (
            data.description.strip()
            if data.description
            else None
        )

        task.project_id = (
            data.project_id
        )

        task.priority = (
            data.priority
        )

        task.due_at = (
            data.due_at
        )

        if data.due_at is None:
            task.deadline_type = None
            task.deadline_confidence = None

        else:
            task.deadline_type = (
                DeadlineType.MANUAL
            )

            task.deadline_confidence = (
                1.0
            )

    else:
        if (
            task.deadline_type
            == DeadlineType.AI_INFERRED
        ):
            if task.due_at is not None:
                task.deadline_type = (
                    DeadlineType.MANUAL
                )

                task.deadline_confidence = (
                    1.0
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
    db: Session = Depends(
        get_db
    ),
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
            detail=(
                "Insufficient permission."
            ),
        )

    task.status = (
        TaskStatus.CANCELLED
    )

    db.commit()
    db.refresh(task)

    return task
