import json
import re
from datetime import datetime, timezone

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.core import SlackMessage, Workspace

broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)
URL_RE = re.compile(r"https?://", re.IGNORECASE)


@dramatiq.actor(actor_name="process_slack_event", max_retries=5, min_backoff=1000)
def process_slack_event(payload: dict) -> None:
    """Persist a Slack event idempotently, then leave it pending for the AI pipeline."""
    event = payload.get("event") or {}
    team_id = payload.get("team_id")

    # MIRANOAH initial policy: DMs are not monitored.
    if event.get("channel_type") == "im":
        return
    if event.get("type") != "message":
        return
    if event.get("subtype") in {"bot_message", "channel_join", "channel_leave"}:
        return

    channel_id = event.get("channel")
    message_ts = event.get("ts")
    if not team_id or not channel_id or not message_ts:
        return

    with SessionLocal() as db:
        workspace = db.scalar(select(Workspace).where(Workspace.slack_team_id == team_id))
        if workspace is None:
            return

        existing = db.scalar(
            select(SlackMessage).where(
                SlackMessage.workspace_id == workspace.id,
                SlackMessage.slack_channel_id == channel_id,
                SlackMessage.message_ts == message_ts,
            )
        )
        if existing:
            return

        text = event.get("text") or ""
        now = datetime.now(timezone.utc)
        db.add(
            SlackMessage(
                workspace_id=workspace.id,
                slack_channel_id=channel_id,
                message_ts=message_ts,
                thread_ts=event.get("thread_ts"),
                slack_user_id=event.get("user"),
                text=text,
                raw_payload=json.dumps(payload, ensure_ascii=False),
                has_files=bool(event.get("files")),
                has_links=bool(URL_RE.search(text)),
                processed=False,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
