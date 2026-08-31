from __future__ import annotations

from typing import Any

import dramatiq

from app.jobs.slack import broker


@dramatiq.actor(
    actor_name="process_slack_action",
    max_retries=5,
    min_backoff=1000,
)
def process_slack_action(
    payload: dict[str, Any],
) -> None:
    """
    Normalize Slack interactive actions.

    This is the transport layer only.

    Future handlers will use this pipeline for:
    - task approval
    - task completion
    - deadline changes
    - assignee changes
    - AI review decisions
    - blocker resolution

    No business entity is mutated here yet.
    """

    action_type = payload.get(
        "type"
    )

    user = payload.get(
        "user"
    ) or {}

    channel = payload.get(
        "channel"
    ) or {}

    message = payload.get(
        "message"
    ) or {}

    actions = payload.get(
        "actions"
    ) or []

    user_id = (
        user.get("id")
        if isinstance(user, dict)
        else None
    )

    channel_id = (
        channel.get("id")
        if isinstance(channel, dict)
        else None
    )

    message_ts = (
        message.get("ts")
        if isinstance(message, dict)
        else None
    )

    print(
        "[MIRANOAH Slack Action]",
        {
            "type": action_type,
            "user_id": user_id,
            "channel_id": channel_id,
            "message_ts": message_ts,
            "actions": actions,
        },
        flush=True,
    )
