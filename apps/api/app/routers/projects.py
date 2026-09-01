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
    require_manager_or_admin,
)
from app.db.session import get_db
from app.models.core import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
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
    stmt = (
        select(Project)
        .where(
            Project.workspace_id
            == current_user.workspace_id
        )
        .order_by(
            Project.created_at.desc()
        )
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
        require_manager_or_admin
    ),
):
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
    project = db.get(
        Project,
        project_id,
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

    return project
