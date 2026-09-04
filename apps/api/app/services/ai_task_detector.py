from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.core import (
    Project,
    SlackChannel,
    SlackMessage,
    User,
)


class TaskDetectionResult(BaseModel):
    is_task: bool

    confidence: float = Field(
        ge=0,
        le=1,
    )

    title: str | None = None
    description: str | None = None

    assignee_slack_user_id: (
        str | None
    ) = None

    project_id: str | None = None

    priority: str = "MEDIUM"

    due_at: datetime | None = None

    deadline_type: str | None = None

    deadline_confidence: (
        float | None
    ) = Field(
        default=None,
        ge=0,
        le=1,
    )


TASK_DETECTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_task": {
            "type": "boolean",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "title": {
            "type": [
                "string",
                "null",
            ],
        },
        "description": {
            "type": [
                "string",
                "null",
            ],
        },
        "assignee_slack_user_id": {
            "type": [
                "string",
                "null",
            ],
        },
        "project_id": {
            "type": [
                "string",
                "null",
            ],
        },
        "priority": {
            "type": "string",
            "enum": [
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            ],
        },
        "due_at": {
            "type": [
                "string",
                "null",
            ],
        },
        "deadline_type": {
            "type": [
                "string",
                "null",
            ],
            "enum": [
                "EXPLICIT",
                "RELATIVE",
                "CALENDAR_BASED",
                "AI_INFERRED",
                "MANUAL",
                None,
            ],
        },
        "deadline_confidence": {
            "type": [
                "number",
                "null",
            ],
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": [
        "is_task",
        "confidence",
        "title",
        "description",
        "assignee_slack_user_id",
        "project_id",
        "priority",
        "due_at",
        "deadline_type",
        "deadline_confidence",
    ],
}


SYSTEM_INSTRUCTIONS = """
あなたはMIRANOAHのTask Detectorです。

Slackメッセージから、
実際に誰かが対応する必要のある仕事・依頼・約束・Todo
が存在するか判定してください。

Taskと判定する例:
- ○○をお願いします
- ○日までに○○してください
- 自分が○○をやります
- ○○を確認して共有します
- ○○を修正してください
- ○○さん、これ対応できますか
- 次回までに○○を準備する

Taskではない例:
- 単なる質問
- 雑談
- 感想
- 進捗報告だけ
- 既に完了した仕事の報告
- 情報共有だけ
- 挨拶

重要ルール:

1.
Taskかどうかを最優先で判定する。

2.
titleは、
「誰が読んでも何をするか分かる」
短い日本語にする。

3.
担当者はSlack本文で明示されている場合、
または発言者本人が明確に
「自分がやる」と宣言した場合だけ設定する。

推測だけで担当者を決めない。

4.
project_idは候補Projectとの関連性が
明確な場合だけ設定する。

曖昧ならnull。

5.
期限について:

本文に
「9/10まで」
「明日」
「来週火曜」
「金曜まで」
など明示的・相対的な期限がある場合、
現在日時を基準にdue_atへ変換する。

直接日付が書かれている:
EXPLICIT

明日・来週火曜等:
RELATIVE

カレンダー上のイベント等を基準:
CALENDAR_BASED

本文に期限が書かれていないのに、
AIが合理的な期限を推測した場合:
AI_INFERRED

期限を設定できない場合:
due_at=null
deadline_type=null

6.
priority:

通常:
MEDIUM

明確に急ぎ:
HIGH

重大障害・今日中に必須等:
CRITICAL

低優先と明示:
LOW

7.
confidenceは、
このメッセージをTaskとして登録してよい確信度。

依頼・期限・担当などが明確なら高くする。

曖昧な会話では低くする。

8.
Slack IDやProject IDは、
与えられた候補に存在するものだけ使用する。

絶対にIDを作らない。
""".strip()


def _get_users(
    *,
    db: Session,
    workspace_id,
) -> list[dict]:
    users = list(
        db.scalars(
            select(User)
            .where(
                User.workspace_id
                == workspace_id,
                User.is_active.is_(True),
            )
            .order_by(
                User.display_name.asc()
            )
        )
    )

    return [
        {
            "slack_user_id": (
                user.slack_user_id
            ),
            "display_name": (
                user.display_name
            ),
        }
        for user in users
        if user.slack_user_id
    ]


def _get_projects(
    *,
    db: Session,
    workspace_id,
) -> list[dict]:
    projects = list(
        db.scalars(
            select(Project)
            .where(
                Project.workspace_id
                == workspace_id
            )
            .order_by(
                Project.created_at.desc()
            )
            .limit(100)
        )
    )

    return [
        {
            "id": str(project.id),
            "name": project.name,
            "description": (
                project.description
            ),
        }
        for project in projects
    ]


def _get_sender(
    *,
    db: Session,
    message: SlackMessage,
) -> dict | None:
    if not message.slack_user_id:
        return None

    user = db.scalar(
        select(User).where(
            User.workspace_id
            == message.workspace_id,
            User.slack_user_id
            == message.slack_user_id,
        )
    )

    if user is None:
        return {
            "slack_user_id": (
                message.slack_user_id
            ),
            "display_name": None,
        }

    return {
        "slack_user_id": (
            user.slack_user_id
        ),
        "display_name": (
            user.display_name
        ),
    }


def _get_channel(
    *,
    db: Session,
    message: SlackMessage,
) -> dict:
    channel = db.scalar(
        select(SlackChannel).where(
            SlackChannel.workspace_id
            == message.workspace_id,
            SlackChannel.slack_channel_id
            == message.slack_channel_id,
        )
    )

    return {
        "slack_channel_id": (
            message.slack_channel_id
        ),
        "name": (
            channel.name
            if channel is not None
            else None
        ),
    }


def detect_task_from_slack_message(
    *,
    db: Session,
    message: SlackMessage,
) -> TaskDetectionResult:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    now_jst = datetime.now(
        ZoneInfo(
            "Asia/Tokyo"
        )
    )

    context = {
        "current_datetime_jst": (
            now_jst.isoformat()
        ),
        "message": {
            "text": message.text,
            "message_ts": (
                message.message_ts
            ),
            "thread_ts": (
                message.thread_ts
            ),
        },
        "sender": _get_sender(
            db=db,
            message=message,
        ),
        "channel": _get_channel(
            db=db,
            message=message,
        ),
        "workspace_users": (
            _get_users(
                db=db,
                workspace_id=(
                    message.workspace_id
                ),
            )
        ),
        "project_candidates": (
            _get_projects(
                db=db,
                workspace_id=(
                    message.workspace_id
                ),
            )
        ),
    }

    client = OpenAI(
        api_key=(
            settings.openai_api_key
        )
    )

    response = client.responses.create(
        model=(
            settings.openai_model_fast
        ),
        instructions=(
            SYSTEM_INSTRUCTIONS
        ),
        input=json.dumps(
            context,
            ensure_ascii=False,
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": (
                    "miranoah_task_detection"
                ),
                "strict": True,
                "schema": (
                    TASK_DETECTION_SCHEMA
                ),
            }
        },
        store=False,
    )

    if not response.output_text:
        raise RuntimeError(
            "OpenAI returned empty output."
        )

    parsed = json.loads(
        response.output_text
    )

    return (
        TaskDetectionResult
        .model_validate(parsed)
    )
