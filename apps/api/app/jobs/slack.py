import json
import re
from datetime import (
    datetime,
    timezone,
)
from typing import Any
from uuid import UUID

import dramatiq
from dramatiq.brokers.redis import (
    RedisBroker,
)
from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.core import (
    Project,
    SlackChannel,
    SlackMessage,
    Task,
    TaskAssignee,
    User,
    Workspace,
)
from app.models.enums import (
    DeadlineType,
    MonitoringPolicy,
    Priority,
    TaskStatus,
)
from app.services.ai_task_detector import (
    detect_task_from_slack_message,
)


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


AI_ENABLED_POLICIES = {
    MonitoringPolicy.MONITOR_FULL,
    MonitoringPolicy.MONITOR_TASK_ONLY,
}


# 0.90以上なら原則自動登録
AUTO_CREATE_THRESHOLD = 0.90

# 0.60未満はReviewにも送らず無視
REVIEW_MIN_THRESHOLD = 0.60


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

    if (
        message.get("subtype")
        == "bot_message"
    ):
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


def _get_channel(
    db: Session,
    workspace_id,
    channel_id: str,
) -> SlackChannel | None:
    return db.scalar(
        select(
            SlackChannel
        ).where(
            SlackChannel.workspace_id
            == workspace_id,
            SlackChannel.slack_channel_id
            == channel_id,
        )
    )


def _channel_is_ignored(
    db: Session,
    workspace_id,
    channel_id: str,
) -> bool:
    channel = _get_channel(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
    )

    if channel is None:
        return False

    return (
        channel.monitoring_policy
        == MonitoringPolicy.IGNORE
    )


def _channel_ai_enabled(
    *,
    db: Session,
    message: SlackMessage,
) -> bool:
    channel = _get_channel(
        db=db,
        workspace_id=(
            message.workspace_id
        ),
        channel_id=(
            message.slack_channel_id
        ),
    )

    if channel is None:
        return True

    return (
        channel.monitoring_policy
        in AI_ENABLED_POLICIES
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
) -> UUID | None:
    message_ts = message.get(
        "ts"
    )

    if not message_ts:
        return None

    if _is_bot_message(
        message
    ):
        return None

    subtype = message.get(
        "subtype"
    )

    if (
        subtype
        in SYSTEM_MESSAGE_SUBTYPES
    ):
        return None

    if not _has_meaningful_content(
        message
    ):
        return None

    existing = _find_message(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
        message_ts=message_ts,
    )

    if existing is not None:
        return existing.id

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
        db.refresh(
            slack_message
        )

        return slack_message.id

    except IntegrityError:
        db.rollback()

        existing = _find_message(
            db=db,
            workspace_id=workspace_id,
            channel_id=channel_id,
            message_ts=message_ts,
        )

        if existing is None:
            return None

        return existing.id


def _update_message(
    db: Session,
    *,
    workspace_id,
    channel_id: str,
    event: dict[str, Any],
    payload: dict[str, Any],
) -> UUID | None:
    message = (
        event.get("message")
        or {}
    )

    if not isinstance(
        message,
        dict,
    ):
        return None

    if _is_bot_message(
        message
    ):
        return None

    message_ts = message.get(
        "ts"
    )

    if not message_ts:
        return None

    existing = _find_message(
        db=db,
        workspace_id=workspace_id,
        channel_id=channel_id,
        message_ts=message_ts,
    )

    if existing is None:
        if not _has_meaningful_content(
            message
        ):
            return None

        return _create_message(
            db=db,
            workspace_id=workspace_id,
            channel_id=channel_id,
            message=message,
            payload=payload,
        )

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

    # 編集されたメッセージは
    # AIに再解析させる
    existing.processed = False

    existing.updated_at = _now()

    db.commit()

    return existing.id


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

    if existing is None:
        return

    now = _now()

    existing.deleted_at = now

    existing.raw_payload = (
        _json_payload(
            payload
        )
    )

    existing.processed = False
    existing.updated_at = now

    db.commit()


def _resolve_user(
    *,
    db: Session,
    workspace_id,
    slack_user_id: str | None,
) -> User | None:
    if not slack_user_id:
        return None

    return db.scalar(
        select(User).where(
            User.workspace_id
            == workspace_id,
            User.slack_user_id
            == slack_user_id,
            User.is_active.is_(True),
        )
    )


def _resolve_project(
    *,
    db: Session,
    workspace_id,
    project_id: str | None,
) -> Project | None:
    if not project_id:
        return None

    try:
        project_uuid = UUID(
            project_id
        )
    except ValueError:
        return None

    project = db.get(
        Project,
        project_uuid,
    )

    if (
        project is None
        or project.workspace_id
        != workspace_id
    ):
        return None

    return project


def _task_fingerprint(
    message: SlackMessage,
) -> str:
    return (
        f"slack:{message.id}"
    )


@dramatiq.actor(
    actor_name=(
        "analyze_slack_message"
    ),
    max_retries=3,
    min_backoff=2000,
)
def analyze_slack_message(
    slack_message_id: str,
) -> None:
    try:
        message_uuid = UUID(
            slack_message_id
        )
    except ValueError:
        return

    with SessionLocal() as db:
        message = db.get(
            SlackMessage,
            message_uuid,
        )

        if message is None:
            return

        if message.deleted_at is not None:
            return

        if message.processed:
            return

        if not (
            message.text
            or ""
        ).strip():
            message.processed = True
            db.commit()
            return

        if not _channel_ai_enabled(
            db=db,
            message=message,
        ):
            message.processed = True
            db.commit()
            return

        if not settings.openai_api_key:
            print(
                "[MIRANOAH AI] "
                "OPENAI_API_KEY is missing."
            )
            return

        fingerprint = (
            _task_fingerprint(
                message
            )
        )

        # 同じSlackメッセージから
        # Taskを重複作成しない
        existing_task = db.scalar(
            select(Task).where(
                Task.workspace_id
                == message.workspace_id,
                Task.task_fingerprint
                == fingerprint,
            )
        )

        if existing_task is not None:
            message.processed = True
            db.commit()
            return

        result = (
            detect_task_from_slack_message(
                db=db,
                message=message,
            )
        )

        print(
            "[MIRANOAH AI] "
            f"message={message.id} "
            f"is_task={result.is_task} "
            f"confidence={result.confidence} "
            f"deadline_type={result.deadline_type}"
        )

        # Taskではない
        if not result.is_task:
            message.processed = True
            db.commit()

            print(
                "[MIRANOAH AI] "
                "Not a task. Ignored."
            )

            return

        # Taskだがタイトル生成に失敗
        if not result.title:
            message.processed = True
            db.commit()

            print(
                "[MIRANOAH AI] "
                "Task title is missing. Ignored."
            )

            return

        # confidence 0.60未満は
        # Reviewにも送らない
        if (
            result.confidence
            < REVIEW_MIN_THRESHOLD
        ):
            message.processed = True
            db.commit()

            print(
                "[MIRANOAH AI] "
                "Ignored because confidence "
                f"is below review threshold "
                f"({result.confidence})."
            )

            return

        requester = _resolve_user(
            db=db,
            workspace_id=(
                message.workspace_id
            ),
            slack_user_id=(
                message.slack_user_id
            ),
        )

        owner = _resolve_user(
            db=db,
            workspace_id=(
                message.workspace_id
            ),
            slack_user_id=(
                result
                .assignee_slack_user_id
            ),
        )

        project = _resolve_project(
            db=db,
            workspace_id=(
                message.workspace_id
            ),
            project_id=(
                result.project_id
            ),
        )

        try:
            priority = Priority(
                result.priority
            )
        except ValueError:
            priority = (
                Priority.MEDIUM
            )

        deadline_type = None

        if result.deadline_type:
            try:
                deadline_type = (
                    DeadlineType(
                        result.deadline_type
                    )
                )
            except ValueError:
                deadline_type = None

        # Reviewが必要な条件
        #
        # 1. Task confidenceが0.90未満
        # 2. 期限をAIが推測している
        requires_review = (
            result.confidence
            < AUTO_CREATE_THRESHOLD
            or deadline_type
            == DeadlineType.AI_INFERRED
        )

        if requires_review:
            task_status = (
                TaskStatus.CANDIDATE
            )
        else:
            task_status = (
                TaskStatus.NOT_STARTED
            )

        task = Task(
            workspace_id=(
                message.workspace_id
            ),
            project_id=(
                project.id
                if project
                else None
            ),
            title=result.title,
            description=(
                result.description
            ),
            status=task_status,
            priority=priority,
            requester_id=(
                requester.id
                if requester
                else None
            ),
            owner_id=(
                owner.id
                if owner
                else None
            ),
            due_at=result.due_at,
            deadline_type=(
                deadline_type
            ),
            deadline_confidence=(
                result
                .deadline_confidence
            ),
            ai_generated=True,
            ai_confidence=(
                result.confidence
            ),
            task_fingerprint=(
                fingerprint
            ),
        )

        db.add(task)
        db.flush()

        if owner is not None:
            db.add(
                TaskAssignee(
                    task_id=task.id,
                    user_id=owner.id,
                )
            )

        message.processed = True

        db.commit()
        db.refresh(task)

        # Review Queueへ送った場合
        if requires_review:
            review_reasons = []

            if (
                result.confidence
                < AUTO_CREATE_THRESHOLD
            ):
                review_reasons.append(
                    "LOW_CONFIDENCE"
                )

            if (
                deadline_type
                == DeadlineType.AI_INFERRED
            ):
                review_reasons.append(
                    "AI_INFERRED_DEADLINE"
                )

            print(
                "[MIRANOAH AI] "
                f"Candidate created: "
                f"{task.id} "
                f"{task.title} "
                f"reasons="
                f"{','.join(review_reasons)}"
            )

            return

        # 高確度なので通常Taskとして自動登録
        print(
            "[MIRANOAH AI] "
            f"Task created: "
            f"{task.id} "
            f"{task.title}"
        )


@dramatiq.actor(
    actor_name=(
        "process_slack_event"
    ),
    max_retries=5,
    min_backoff=1000,
)
def process_slack_event(
    payload: dict,
) -> None:
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

    # DMは対象外
    if _is_dm(
        event
    ):
        return

    if (
        event.get("type")
        != "message"
    ):
        return

    channel_id = event.get(
        "channel"
    )

    if (
        not team_id
        or not channel_id
    ):
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

        # IGNORE設定のチャンネルは
        # 保存も解析もしない
        if _channel_is_ignored(
            db=db,
            workspace_id=(
                workspace.id
            ),
            channel_id=channel_id,
        ):
            return

        subtype = event.get(
            "subtype"
        )

        # Slackメッセージ編集
        if (
            subtype
            == "message_changed"
        ):
            message_id = (
                _update_message(
                    db=db,
                    workspace_id=(
                        workspace.id
                    ),
                    channel_id=(
                        channel_id
                    ),
                    event=event,
                    payload=payload,
                )
            )

            if message_id:
                analyze_slack_message.send(
                    str(message_id)
                )

            return

        # Slackメッセージ削除
        if (
            subtype
            == "message_deleted"
        ):
            _delete_message(
                db=db,
                workspace_id=(
                    workspace.id
                ),
                channel_id=(
                    channel_id
                ),
                event=event,
                payload=payload,
            )

            return

        if (
            subtype
            in SYSTEM_MESSAGE_SUBTYPES
        ):
            return

        # 通常メッセージ
        message_id = (
            _create_message(
                db=db,
                workspace_id=(
                    workspace.id
                ),
                channel_id=(
                    channel_id
                ),
                message=event,
                payload=payload,
            )
        )

        # DB保存後、
        # AI Task Detectorへ送る
        if message_id:
            analyze_slack_message.send(
                str(message_id)
            )
