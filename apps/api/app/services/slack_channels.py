from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import SlackChannel, Workspace
from app.models.enums import MonitoringPolicy
from app.services.slack_api import SlackAPIClient, SlackAPIError


@dataclass
class SlackChannelSyncResult:
    workspace_id: str
    slack_team_id: str

    fetched: int
    created: int
    updated: int
    archived: int


def _fetch_all_channels(
    client: SlackAPIClient,
) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []

    cursor: str | None = None

    while True:
        response = client.conversations_list(
            cursor=cursor,
            limit=200,
        )

        page_channels = response.get("channels") or []

        if not isinstance(page_channels, list):
            raise SlackAPIError(
                "Slack conversations.list returned an invalid channels field."
            )

        channels.extend(page_channels)

        response_metadata = (
            response.get("response_metadata")
            or {}
        )

        next_cursor = response_metadata.get(
            "next_cursor"
        )

        if not isinstance(next_cursor, str):
            next_cursor = ""

        next_cursor = next_cursor.strip()

        if not next_cursor:
            break

        cursor = next_cursor

    return channels


def sync_slack_channels(
    db: Session,
    client: SlackAPIClient | None = None,
) -> SlackChannelSyncResult:
    client = client or SlackAPIClient()

    auth = client.auth_test()

    slack_team_id = auth.get("team_id")

    if not slack_team_id:
        raise SlackAPIError(
            "Slack auth.test did not return team_id."
        )

    workspace = db.scalar(
        select(Workspace).where(
            Workspace.slack_team_id
            == slack_team_id
        )
    )

    if workspace is None:
        raise SlackAPIError(
            f"No MIRANOAH workspace is mapped to Slack team {slack_team_id}."
        )

    channels = _fetch_all_channels(client)

    existing_channels = db.scalars(
        select(SlackChannel).where(
            SlackChannel.workspace_id
            == workspace.id
        )
    ).all()

    existing_by_slack_id = {
        channel.slack_channel_id: channel
        for channel in existing_channels
    }

    created = 0
    updated = 0
    archived = 0

    for slack_channel in channels:
        slack_channel_id = slack_channel.get("id")

        if not slack_channel_id:
            continue

        name = slack_channel.get("name")

        if not isinstance(name, str):
            name = None

        is_private = bool(
            slack_channel.get(
                "is_private",
                False,
            )
        )

        is_archived = bool(
            slack_channel.get(
                "is_archived",
                False,
            )
        )

        channel = existing_by_slack_id.get(
            slack_channel_id
        )

        if channel is None:
            channel = SlackChannel(
                workspace_id=workspace.id,
                slack_channel_id=slack_channel_id,
                name=name,
                is_private=is_private,
                monitoring_policy=(
                    MonitoringPolicy.IGNORE
                    if is_archived
                    else MonitoringPolicy.MONITOR_TASK_ONLY
                ),
            )

            db.add(channel)

            existing_by_slack_id[
                slack_channel_id
            ] = channel

            created += 1

            if is_archived:
                archived += 1

            continue

        changed = False

        if channel.name != name:
            channel.name = name
            changed = True

        if channel.is_private != is_private:
            channel.is_private = is_private
            changed = True

        if (
            is_archived
            and channel.monitoring_policy
            != MonitoringPolicy.IGNORE
        ):
            channel.monitoring_policy = (
                MonitoringPolicy.IGNORE
            )

            archived += 1
            changed = True

        if changed:
            updated += 1

    db.commit()

    return SlackChannelSyncResult(
        workspace_id=str(workspace.id),
        slack_team_id=slack_team_id,
        fetched=len(channels),
        created=created,
        updated=updated,
        archived=archived,
    )


def sync_slack_channels_as_dict(
    db: Session,
    client: SlackAPIClient | None = None,
) -> dict[str, Any]:
    result = sync_slack_channels(
        db=db,
        client=client,
    )

    return asdict(result)
