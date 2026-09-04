from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.db.session import get_db
from app.models.core import (
    Project,
    ProjectMember,
    User,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberRead,
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


def get_visible_project(
    *,
    db: Session,
    current_user: CurrentUser,
    project_id: UUID,
) -> Project:
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
    if not has_global_permission(
        db=db,
        current_user=current_user,
        permission="project.create",
    ):
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
        workspace_id=current_user.workspace_id,
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
    return get_visible_project(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )


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
    project = get_visible_project(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )

    if not has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project.id,
        permission="project.edit",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    payload = data.model_dump(
        exclude_unset=True
    )

    if (
        "owner_id" in payload
        and payload["owner_id"] is not None
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
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    return project


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberRead],
)
def list_project_members(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    project = get_visible_project(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )

    if not has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project.id,
        permission="member.view",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    return list(
        db.scalars(
            select(ProjectMember).where(
                ProjectMember.project_id
                == project.id
            )
        )
    )


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberRead,
    status_code=201,
)
def add_project_member(
    project_id: UUID,
    data: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    project = get_visible_project(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )

    if not has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project.id,
        permission="project.member.manage",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    user = db.get(
        User,
        data.user_id,
    )

    if (
        user is None
        or user.workspace_id
        != current_user.workspace_id
    ):
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=data.role,
    )

    db.add(member)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="User is already a project member.",
        )

    db.refresh(member)

    return member


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=204,
)
def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    project = get_visible_project(
        db=db,
        current_user=current_user,
        project_id=project_id,
    )

    if not has_project_permission(
        db=db,
        current_user=current_user,
        project_id=project.id,
        permission="project.member.manage",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id
            == project.id,
            ProjectMember.user_id
            == user_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=404,
            detail="Project member not found.",
        )

    db.delete(member)
    db.commit()

    return None
