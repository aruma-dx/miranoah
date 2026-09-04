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
    Team,
    TeamMember,
    User,
)
from app.models.enums import WorkspaceRole
from app.models.team_project import TeamProject
from app.schemas.project import ProjectRead
from app.schemas.team import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberRead,
    TeamRead,
    TeamUpdate,
)
from app.services.authorization import (
    has_global_permission,
    has_team_permission,
)


router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
)


def apply_team_view_scope(
    stmt,
    current_user: CurrentUser,
):
    stmt = stmt.where(
        Team.workspace_id
        == current_user.workspace_id
    )

    if (
        current_user.is_workspace_owner
        or current_user.workspace_role
        == WorkspaceRole.ADMIN
    ):
        return stmt

    return (
        stmt
        .join(
            TeamMember,
            TeamMember.team_id == Team.id,
        )
        .where(
            TeamMember.user_id
            == current_user.id
        )
    )


def get_visible_team(
    *,
    db: Session,
    current_user: CurrentUser,
    team_id: UUID,
) -> Team:
    stmt = select(Team).where(
        Team.id == team_id
    )

    stmt = apply_team_view_scope(
        stmt,
        current_user,
    )

    team = db.scalar(stmt)

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found.",
        )

    return team


@router.get(
    "",
    response_model=list[TeamRead],
)
def list_teams(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    stmt = apply_team_view_scope(
        select(Team),
        current_user,
    )

    return list(
        db.scalars(
            stmt.order_by(
                Team.name.asc()
            )
        )
    )


@router.post(
    "",
    response_model=TeamRead,
    status_code=201,
)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    if not has_global_permission(
        db=db,
        current_user=current_user,
        permission="team.create",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    team = Team(
        workspace_id=current_user.workspace_id,
        name=data.name,
        description=data.description,
    )

    db.add(team)
    db.flush()

    # 作成者を自動的にTeam MANAGERへ登録
    member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role="MANAGER",
    )

    db.add(member)
    db.commit()
    db.refresh(team)

    return team


@router.get(
    "/{team_id}",
    response_model=TeamRead,
)
def get_team(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    return get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )


@router.patch(
    "/{team_id}",
    response_model=TeamRead,
)
def update_team(
    team_id: UUID,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="team.edit",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    payload = data.model_dump(
        exclude_unset=True
    )

    for key, value in payload.items():
        setattr(team, key, value)

    db.commit()
    db.refresh(team)

    return team


@router.get(
    "/{team_id}/members",
    response_model=list[TeamMemberRead],
)
def list_team_members(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="member.view",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    return list(
        db.scalars(
            select(TeamMember).where(
                TeamMember.team_id == team.id
            )
        )
    )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=201,
)
def add_team_member(
    team_id: UUID,
    data: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="team.member.manage",
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

    member = TeamMember(
        team_id=team.id,
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
            detail="User is already a team member.",
        )

    db.refresh(member)

    return member


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=204,
)
def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="team.member.manage",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=404,
            detail="Team member not found.",
        )

    db.delete(member)
    db.commit()

    return None


@router.get(
    "/{team_id}/projects",
    response_model=list[ProjectRead],
)
def list_team_projects(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    stmt = (
        select(Project)
        .join(
            TeamProject,
            TeamProject.project_id
            == Project.id,
        )
        .where(
            TeamProject.team_id
            == team.id,
            Project.workspace_id
            == current_user.workspace_id,
        )
        .order_by(
            Project.created_at.desc()
        )
    )

    return list(
        db.scalars(stmt)
    )


@router.post(
    "/{team_id}/projects/{project_id}",
    status_code=201,
)
def link_team_project(
    team_id: UUID,
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="team.project.manage",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

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
            detail="Project not found.",
        )

    link = TeamProject(
        team_id=team.id,
        project_id=project.id,
    )

    db.add(link)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Project is already linked.",
        )

    return {
        "team_id": str(team.id),
        "project_id": str(project.id),
    }


@router.delete(
    "/{team_id}/projects/{project_id}",
    status_code=204,
)
def unlink_team_project(
    team_id: UUID,
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    team = get_visible_team(
        db=db,
        current_user=current_user,
        team_id=team_id,
    )

    if not has_team_permission(
        db=db,
        current_user=current_user,
        team_id=team.id,
        permission="team.project.manage",
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission.",
        )

    link = db.scalar(
        select(TeamProject).where(
            TeamProject.team_id == team.id,
            TeamProject.project_id
            == project_id,
        )
    )

    if link is None:
        raise HTTPException(
            status_code=404,
            detail="Team project link not found.",
        )

    db.delete(link)
    db.commit()

    return None
