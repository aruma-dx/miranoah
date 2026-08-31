from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.slack_api import (
    SlackAPIClient,
    SlackAPIError,
)


@dataclass
class SlackSendResult:
    channel: str
    ts: str
    text: str


def send_slack_message(
    *,
    channel_id: str,
    text: str,
    thread_ts: str | None = None,
    client: SlackAPIClient | None = None,
) -> SlackSendResult:
    if not channel_id.strip():
        raise ValueError(
            "channel_id is required."
        )

    if not text.strip():
        raise ValueError(
            "text is required."
        )

    client = client or SlackAPIClient()

    response = client.chat_post_message(
        channel=channel_id,
        text=text,
        thread_ts=thread_ts,
    )

    channel = response.get("channel")
    ts = response.get("ts")

    if not channel or not ts:
        raise SlackAPIError(
            "Slack chat.postMessage did not return channel or ts."
        )

    return SlackSendResult(
        channel=channel,
        ts=ts,
        text=text,
    )


def send_slack_message_as_dict(
    *,
    channel_id: str,
    text: str,
    thread_ts: str | None = None,
    client: SlackAPIClient | None = None,
) -> dict[str, Any]:
    result = send_slack_message(
        channel_id=channel_id,
        text=text,
        thread_ts=thread_ts,
        client=client,
    )

    return asdict(result)
