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
from app.models.core import (
    Project,
    User,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.authorization import (
    has_global_permission,
    has_project_permission,
)
from app.services.scopes import (
    apply_project_view_scope,
)


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["projects"],
)


@router.get(
    "",
    response_model=list[ProjectRead],
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = select(Project)

    stmt = apply_project_view_scope(
        stmt=stmt,
        current_user=current_user,
    )

    stmt = stmt.order_by(
        Project.created_at.desc()
    )

    return list(
        db.scalars(stmt)
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=201,
)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    allowed = has_global_permission(
        db=db,
        current_user=current_user,
        permission="project.create",
    )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
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

    project = Project(
        workspace_id=(
            current_user.workspace_id
        ),
        **data.model_dump(),
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = select(Project).where(
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
            detail="Project not found",
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = select(Project).where(
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
            detail="Project not found",
        )

    allowed = has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project.id,
        permission="project.edit",
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
            project,
            key,
            value,
        )

    db.commit()
    db.refresh(project)

    return project
