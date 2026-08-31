import json
import re
from datetime import datetime, timezone
from typing import Any

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.core import (
    SlackChannel,
    SlackMessage,
    Workspace,
)
from app.models.enums import MonitoringPolicy


broker = RedisBroker(
    url=settings.redis_url
)

dramatiq.set_broker(
    broker
)

URL_RE = re.compile(
    r"https?://",
    re.IGNORECASE,
)


SYSTEM_MESSAGE_SUBTYPES = {
    "bot_message",
    "channel_join",
    "channel_leave",
    "channel_name",
    "channel_purpose",
    "channel_topic",
    "channel_archive",
    "channel_unarchive",
    "group_join",
    "group_leave",
    "tombstone",
    "pinned_item",
    "unpinned_item",
    "ekm_access_denied",
}


def _now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _json_payload(
    payload: dict[str, Any],
) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
    )


def _is_dm(
    event: dict[str, Any],
) -> bool:
    return (
        event.get("channel_type")
        == "im"
    )


def _is_bot_message(
    message: dict[str, Any],
) -> bool:
    if message.get("bot_id"):
        return True

    if message.get("subtype") == "bot_message":
        return True

    return False


def _has_meaningful_content(
    message: dict[str, Any],
) -> bool:
    text = (
        message.get("text")
        or ""
    ).strip()

    files = (
        message.get("files")
        or []
    )

    return bool(
        text or files
    )


def _channel_is_ignored(
    db: Session,
    workspace_id,
    channel_id: str,
) -> bool:
    channel = db.scalar(
        select(
            SlackChannel
        ).where(
            SlackChannel.workspace_id
            == workspace_id,
            SlackChannel.slack_channel_id
            == channel_id,
        )
    )

    if channel is None:
        return False

    return (
        channel.monitoring_policy
        == MonitoringPolicy.IGNORE
    )


def _find_message(
    db: Session,
    workspace_id,
    channel_id: str,
    message_ts: str,
) -> SlackMessage | None:
    return db.scalar(
        select(
            SlackMessage
        ).where(
            SlackMessage.workspace_id
            == workspace_id,
            SlackMessage.slack_channel_id
            == channel_id,
            SlackMessage.message_ts
            == message_ts,
        )
    )


def _create_message(
    db: Session,
    *,
    workspace_id,
    channel_id: str,
    message: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    message_ts = message.get(
        "ts"
    )

    if not message_ts:
        return

    if _is_bot_message(
        message
    ):
        return

    subtype = message.get(
        "subtype"
    )

    if subtype in SYSTEM_MESSAGE_SUBTYPES:
        return

    if not _has_meaningful_content(
        message
    ):
        return

    existing = _find_message(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
        message_ts=message_ts,
    )

    if existing is not None:
        return

    text = (
        message.get("text")
        or ""
    )

    now = _now()

    slack_message = SlackMessage(
        workspace_id=workspace_id,
        slack_channel_id=channel_id,
        message_ts=message_ts,
        thread_ts=message.get(
            "thread_ts"
        ),
        slack_user_id=message.get(
            "user"
        ),
        text=text,
        raw_payload=_json_payload(
            payload
        ),
        has_files=bool(
            message.get("files")
        ),
        has_links=bool(
            URL_RE.search(text)
        ),
        processed=False,
        created_at=now,
        updated_at=now,
    )

    db.add(
        slack_message
    )

    try:
        db.commit()

    except IntegrityError:
        # Slack can redeliver the same event,
        # and multiple workers may process it concurrently.
        # The DB unique constraint is the final idempotency guard.
        db.rollback()


def _update_message(
    db: Session,
    *,
    workspace_id,
    channel_id: str,
    event: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    message = (
        event.get("message")
        or {}
    )

    if not isinstance(
        message,
        dict,
    ):
        return

    if _is_bot_message(
        message
    ):
        return

    message_ts = message.get(
        "ts"
    )

    if not message_ts:
        return

    existing = _find_message(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
        message_ts=message_ts,
    )

    # If MIRANOAH never received the original message,
    # an edit event can still be used to create the current version.
    if existing is None:
        if not _has_meaningful_content(
            message
        ):
            return

        _create_message(
            db=db,
            workspace_id=workspace_id,
            channel_id=channel_id,
            message=message,
            payload=payload,
        )

        return

    text = (
        message.get("text")
        or ""
    )

    existing.thread_ts = (
        message.get("thread_ts")
    )

    existing.slack_user_id = (
        message.get("user")
        or existing.slack_user_id
    )

    existing.text = text

    existing.raw_payload = (
        _json_payload(
            payload
        )
    )

    existing.has_files = bool(
        message.get("files")
    )

    existing.has_links = bool(
        URL_RE.search(text)
    )

    existing.edited_at = _now()

    # Edited messages must be analyzed again
    # by the future AI pipeline.
    existing.processed = False

    existing.updated_at = _now()

    db.commit()


def _delete_message(
    db: Session,
    *,
    workspace_id,
    channel_id: str,
    event: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    message_ts = event.get(
        "deleted_ts"
    )

    if not message_ts:
        previous_message = (
            event.get(
                "previous_message"
            )
            or {}
        )

        if isinstance(
            previous_message,
            dict,
        ):
            message_ts = (
                previous_message.get(
                    "ts"
                )
            )

    if not message_ts:
        return

    existing = _find_message(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
        message_ts=message_ts,
    )

    # Do not create empty tombstone records.
    # If the original message does not exist,
    # there is nothing useful to soft-delete.
    if existing is None:
        return

    now = _now()

    existing.deleted_at = now

    existing.raw_payload = (
        _json_payload(
            payload
        )
    )

    # Future AI reconciliation needs to know
    # that the source message was deleted.
    existing.processed = False

    existing.updated_at = now

    db.commit()


@dramatiq.actor(
    actor_name="process_slack_event",
    max_retries=5,
    min_backoff=1000,
)
def process_slack_event(
    payload: dict,
) -> None:
    """
    Normalize and persist Slack message events.

    Supported:
    - normal messages
    - thread messages
    - file messages
    - message_changed
    - message_deleted
    - Slack retries

    Ignored:
    - DMs
    - bot/app messages
    - system messages
    - empty messages
    - channels configured as IGNORE
    """

    event = (
        payload.get("event")
        or {}
    )

    team_id = payload.get(
        "team_id"
    )

    if not isinstance(
        event,
        dict,
    ):
        return

    if _is_dm(
        event
    ):
        return

    if event.get("type") != "message":
        return

    channel_id = event.get(
        "channel"
    )

    if not team_id or not channel_id:
        return

    with SessionLocal() as db:
        workspace = db.scalar(
            select(
                Workspace
            ).where(
                Workspace.slack_team_id
                == team_id
            )
        )

        if workspace is None:
            return

        if _channel_is_ignored(
            db=db,
            workspace_id=workspace.id,
            channel_id=channel_id,
        ):
            return

        subtype = event.get(
            "subtype"
        )

        if subtype == "message_changed":
            _update_message(
                db=db,
                workspace_id=workspace.id,
                channel_id=channel_id,
                event=event,
                payload=payload,
            )

            return

        if subtype == "message_deleted":
            _delete_message(
                db=db,
                workspace_id=workspace.id,
                channel_id=channel_id,
                event=event,
                payload=payload,
            )

            return

        if subtype in SYSTEM_MESSAGE_SUBTYPES:
            return

        _create_message(
            db=db,
            workspace_id=workspace.id,
            channel_id=channel_id,
            message=event,
            payload=payload,
        )
