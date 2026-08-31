from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, Workspace
from app.models.enums import WorkspaceRole
from app.services.slack_api import SlackAPIClient, SlackAPIError


@dataclass
class SlackUserSyncResult:
    workspace_id: str
    slack_team_id: str

    fetched: int
    human_users: int

    created: int
    updated: int
    deactivated: int

    skipped_bots: int


def _get_display_name(member: dict[str, Any]) -> str:
    profile = member.get("profile") or {}

    candidates = [
        profile.get("display_name"),
        profile.get("real_name"),
        member.get("real_name"),
        member.get("name"),
        member.get("id"),
    ]

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Unknown User"


def _get_email(member: dict[str, Any]) -> str | None:
    profile = member.get("profile") or {}

    email = profile.get("email")

    if not isinstance(email, str):
        return None

    email = email.strip()

    return email or None


def _is_bot(member: dict[str, Any]) -> bool:
    slack_user_id = member.get("id")

    if slack_user_id == "USLACKBOT":
        return True

    if member.get("is_bot"):
        return True

    if member.get("is_app_user"):
        return True

    return False


def _fetch_all_slack_users(
    client: SlackAPIClient,
) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []

    cursor: str | None = None

    while True:
        response = client.users_list(
            cursor=cursor,
            limit=200,
        )

        page_members = response.get("members") or []

        if not isinstance(page_members, list):
            raise SlackAPIError(
                "Slack users.list returned an invalid members field."
            )

        members.extend(page_members)

        response_metadata = response.get("response_metadata") or {}

        next_cursor = response_metadata.get("next_cursor")

        if not isinstance(next_cursor, str):
            next_cursor = ""

        next_cursor = next_cursor.strip()

        if not next_cursor:
            break

        cursor = next_cursor

    return members


def sync_slack_users(
    db: Session,
    client: SlackAPIClient | None = None,
) -> SlackUserSyncResult:
    client = client or SlackAPIClient()

    auth = client.auth_test()

    slack_team_id = auth.get("team_id")

    if not slack_team_id:
        raise SlackAPIError(
            "Slack auth.test did not return team_id."
        )

    workspace = db.scalar(
        select(Workspace).where(
            Workspace.slack_team_id == slack_team_id
        )
    )

    if workspace is None:
        raise SlackAPIError(
            f"No MIRANOAH workspace is mapped to Slack team {slack_team_id}."
        )

    members = _fetch_all_slack_users(client)

    existing_users = db.scalars(
        select(User).where(
            User.workspace_id == workspace.id
        )
    ).all()

    existing_by_slack_id = {
        user.slack_user_id: user
        for user in existing_users
        if user.slack_user_id
    }

    active_human_slack_ids: set[str] = set()

    created = 0
    updated = 0
    skipped_bots = 0
    human_users = 0

    for member in members:
        slack_user_id = member.get("id")

        if not slack_user_id:
            continue

        if _is_bot(member):
            skipped_bots += 1
            continue

        human_users += 1

        is_deleted = bool(member.get("deleted", False))
        is_active = not is_deleted

        if is_active:
            active_human_slack_ids.add(slack_user_id)

        display_name = _get_display_name(member)
        email = _get_email(member)

        user = existing_by_slack_id.get(slack_user_id)

        if user is None:
            user = User(
                workspace_id=workspace.id,
                slack_user_id=slack_user_id,
                email=email,
                display_name=display_name,
                workspace_role=WorkspaceRole.PLAYER,
                is_workspace_owner=False,
                is_active=is_active,
            )

            db.add(user)

            existing_by_slack_id[slack_user_id] = user

            created += 1

            continue

        changed = False

        if user.display_name != display_name:
            user.display_name = display_name
            changed = True

        if user.email != email:
            user.email = email
            changed = True

        if user.is_active != is_active:
            user.is_active = is_active
            changed = True

        if changed:
            updated += 1

    deactivated = 0

    for user in existing_users:
        if not user.slack_user_id:
            continue

        if user.slack_user_id in active_human_slack_ids:
            continue

        if user.is_active:
            user.is_active = False
            deactivated += 1

    db.commit()

    return SlackUserSyncResult(
        workspace_id=str(workspace.id),
        slack_team_id=slack_team_id,
        fetched=len(members),
        human_users=human_users,
        created=created,
        updated=updated,
        deactivated=deactivated,
        skipped_bots=skipped_bots,
    )


def sync_slack_users_as_dict(
    db: Session,
    client: SlackAPIClient | None = None,
) -> dict[str, Any]:
    result = sync_slack_users(
        db=db,
        client=client,
    )

    return asdict(result)
