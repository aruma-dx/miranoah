from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.core import (
    Project,
    SlackChannel,
    SlackMessage,
    User,
)


# 通常チャンネル会話では
# 対象メッセージより前の何件を見るか
CHANNEL_CONTEXT_LIMIT = 5

# スレッドでは親投稿を含め
# 最大何件を見るか
THREAD_CONTEXT_LIMIT = 20


SLACK_MENTION_RE = re.compile(
    r"<@([A-Z0-9]+)>"
)


ASSIGNMENT_MARKERS = (
    "お願い",
    "お願いします",
    "対応して",
    "対応お願い",
    "確認して",
    "確認お願い",
    "修正して",
    "修正お願い",
    "作成して",
    "作って",
    "共有して",
    "準備して",
    "送って",
    "送付して",
    "提出して",
    "更新して",
    "調整して",
    "連絡して",
    "進めて",
    "やって",
    "してください",
    "できますか",
    "お願いできますか",
    "頼む",
    "任せ",
)


SELF_COMMITMENT_MARKERS = (
    "やります",
    "やっておきます",
    "対応します",
    "対応しておきます",
    "確認します",
    "確認しておきます",
    "修正します",
    "修正しておきます",
    "作成します",
    "作ります",
    "準備します",
    "共有します",
    "送ります",
    "送付します",
    "提出します",
    "更新します",
    "調整します",
    "連絡します",
    "進めます",
    "進めておきます",
    "担当します",
    "対応しておきます",
)


class TaskDetectionResult(
    BaseModel
):
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

    project_id: (
        str | None
    ) = None

    priority: str = "MEDIUM"

    due_at: (
        datetime | None
    ) = None

    deadline_type: (
        str | None
    ) = None

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

Slack上の対象メッセージと、その前後関係を理解するための
会話コンテキストが与えられます。

対象メッセージを中心に、
実際に誰かが対応する必要のある
仕事・依頼・約束・Todoが存在するか判定してください。


【最重要】

conversation_contextは、
対象メッセージの意味を理解するための補助情報です。

Task化するかどうかは、
target_messageを中心に判断してください。

過去の会話にTaskが存在するだけで、
今回のtarget_messageまで
新しいTaskとして登録してはいけません。


Taskと判定する例:

- ○○をお願いします
- ○日までに○○してください
- 自分が○○をやります
- ○○を確認して共有します
- ○○を修正してください
- ○○さん、これ対応できますか
- 次回までに○○を準備する

また、対象メッセージ単体では意味が不足していても、
直前の会話やスレッドから作業内容が明確になる場合は、
文脈を補完してTaskとして判定してよい。

例:

A:
「企画書の修正版どうなっていますか？」

B:
「今日中にやります」

この場合、
target_messageがBの発言なら、
「企画書の修正版を今日中に対応する」
というTaskとして解釈できる。


Taskではない例:

- 単なる質問
- 雑談
- 感想
- 進捗報告だけ
- 既に完了した仕事の報告
- 情報共有だけ
- 挨拶
- 過去Taskに対する単なる了解
- 「ありがとうございます」
- 「確認しました」だけ
- conversation_contextにTaskがあるだけで、
  target_message自身には新しい依頼・約束・対応がない場合


重要ルール:


1.
Taskかどうかを最優先で判定する。


2.
titleは、
会話コンテキストを踏まえて、

「誰が読んでも何をするか分かる」

短い日本語にする。

「これをやる」
「確認する」
など、
対象が分からないタイトルは禁止。

コンテキストから対象を具体化する。


3.
descriptionには必要に応じて、
Taskを理解するための補足を書く。

無理に長文化しない。


4.
担当者は、

- Slack本文で明示されている
- 会話コンテキストから
  誰に依頼しているか明確
- 発言者本人が
  「自分がやる」と明確に宣言

のいずれかの場合だけ設定する。

推測だけで担当者を決めない。


5.
メンション表現
<@SLACK_USER_ID>
が存在する場合は、
workspace_usersから対応する人物を確認する。

Slack User IDは必ず
workspace_usersに存在するIDだけを使用する。

複数人が同じTaskの担当者として
明示されている場合は、
単一担当者を勝手に選ばずnullとする。


6.
project_idは、
Project候補との関連性が明確な場合だけ設定する。

target_messageだけでは分からなくても、
conversation_contextから
Projectが明確に特定できる場合は設定してよい。

曖昧ならnull。


7.
期限について:

対象メッセージまたは、
その対象メッセージが参照している会話に

「9/10まで」
「明日」
「来週火曜」
「金曜まで」
「今日中」

など明示的・相対的な期限がある場合、
現在日時を基準にdue_atへ変換する。


直接日付が書かれている:
EXPLICIT


明日・今日中・来週火曜等:
RELATIVE


カレンダー上のイベント等を基準:
CALENDAR_BASED


期限が明示されていないのに、
AIが合理的な期限を推測した場合:
AI_INFERRED


期限を設定できない場合:

due_at=null
deadline_type=null


8.
会話内で古い期限と新しい期限が競合する場合、
target_messageに最も近い、
最新の明確な期限を優先する。


9.
priority:

通常:
MEDIUM

明確に急ぎ:
HIGH

重大障害・今日中に必須等:
CRITICAL

低優先と明示:
LOW


10.
confidenceは、

「conversation_contextを含めて考えた結果、
このtarget_messageからTaskを登録してよい確信度」

として評価する。


依頼内容・担当者・期限などが明確:
高いconfidence


会話から内容をかなり推測する必要がある:
低めのconfidence


11.
conversation_context内で、
target_messageには

"is_target": true

が付いています。

必ずこのメッセージを中心に判定する。


12.
Slack IDやProject IDは、
与えられた候補に存在するものだけ使用する。

絶対にIDを作らない。


13.
同じ会話の過去メッセージで既に依頼があり、
target_messageが単なる

「了解です」
「承知しました」
「ありがとうございます」

だけの場合は、
新しいTaskとして重複登録しない。

ただし、

「了解です。今日中に対応します」

のように、
target_messageで明確な実行約束が追加された場合は
Taskとして扱ってよい。
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

                User.is_active.is_(
                    True
                ),
            )
            .order_by(
                User.display_name.asc()
            )
        )
    )

    return [
        {
            "slack_user_id":
                user.slack_user_id,

            "display_name":
                user.display_name,
        }
        for user in users
        if user.slack_user_id
    ]


def _get_user_map(
    *,
    db: Session,
    workspace_id,
) -> dict[str, str]:
    users = list(
        db.scalars(
            select(User).where(
                User.workspace_id
                == workspace_id,

                User.is_active.is_(
                    True
                ),
            )
        )
    )

    return {
        user.slack_user_id:
            user.display_name

        for user in users

        if user.slack_user_id
    }


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
            "id":
                str(
                    project.id
                ),

            "name":
                project.name,

            "description":
                project.description,
        }
        for project
        in projects
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
            "slack_user_id":
                message.slack_user_id,

            "display_name":
                None,
        }

    return {
        "slack_user_id":
            user.slack_user_id,

        "display_name":
            user.display_name,
    }


def _get_channel(
    *,
    db: Session,
    message: SlackMessage,
) -> dict:
    channel = db.scalar(
        select(
            SlackChannel
        ).where(
            SlackChannel.workspace_id
            == message.workspace_id,

            SlackChannel.slack_channel_id
            == message.slack_channel_id,
        )
    )

    return {
        "slack_channel_id":
            message.slack_channel_id,

        "name": (
            channel.name
            if channel is not None
            else None
        ),
    }


def _serialize_message(
    *,
    message: SlackMessage,
    user_map: dict[str, str],
    target_message_id,
) -> dict:
    sender_name = None

    if message.slack_user_id:
        sender_name = user_map.get(
            message.slack_user_id
        )

    return {
        "id":
            str(
                message.id
            ),

        "message_ts":
            message.message_ts,

        "thread_ts":
            message.thread_ts,

        "slack_user_id":
            message.slack_user_id,

        "sender_name":
            sender_name,

        "text":
            message.text,

        "is_target":
            message.id
            == target_message_id,
    }


def _get_thread_context(
    *,
    db: Session,
    message: SlackMessage,
    user_map: dict[str, str],
) -> list[dict]:
    root_ts = (
        message.thread_ts
        or message.message_ts
    )

    stmt = (
        select(
            SlackMessage
        )
        .where(
            SlackMessage.workspace_id
            == message.workspace_id,

            SlackMessage.slack_channel_id
            == message.slack_channel_id,

            SlackMessage.deleted_at.is_(
                None
            ),

            SlackMessage.message_ts
            <= message.message_ts,

            or_(
                SlackMessage.message_ts
                == root_ts,

                SlackMessage.thread_ts
                == root_ts,
            ),
        )
        .order_by(
            SlackMessage.message_ts.asc()
        )
        .limit(
            THREAD_CONTEXT_LIMIT
        )
    )

    messages = list(
        db.scalars(
            stmt
        )
    )

    return [
        _serialize_message(
            message=item,
            user_map=user_map,
            target_message_id=(
                message.id
            ),
        )
        for item
        in messages
    ]


def _get_channel_context(
    *,
    db: Session,
    message: SlackMessage,
    user_map: dict[str, str],
) -> list[dict]:
    previous_stmt = (
        select(
            SlackMessage
        )
        .where(
            SlackMessage.workspace_id
            == message.workspace_id,

            SlackMessage.slack_channel_id
            == message.slack_channel_id,

            SlackMessage.deleted_at.is_(
                None
            ),

            SlackMessage.message_ts
            < message.message_ts,

            SlackMessage.thread_ts.is_(
                None
            ),
        )
        .order_by(
            SlackMessage.message_ts.desc()
        )
        .limit(
            CHANNEL_CONTEXT_LIMIT
        )
    )

    previous_messages = list(
        db.scalars(
            previous_stmt
        )
    )

    previous_messages.reverse()

    messages = [
        *previous_messages,
        message,
    ]

    return [
        _serialize_message(
            message=item,
            user_map=user_map,
            target_message_id=(
                message.id
            ),
        )
        for item
        in messages
    ]


def _get_conversation_context(
    *,
    db: Session,
    message: SlackMessage,
) -> dict:
    user_map = _get_user_map(
        db=db,
        workspace_id=(
            message.workspace_id
        ),
    )

    if message.thread_ts:
        messages = (
            _get_thread_context(
                db=db,
                message=message,
                user_map=user_map,
            )
        )

        context_type = (
            "THREAD"
        )

    else:
        messages = (
            _get_channel_context(
                db=db,
                message=message,
                user_map=user_map,
            )
        )

        context_type = (
            "CHANNEL_RECENT"
        )

    return {
        "context_type":
            context_type,

        "message_count":
            len(
                messages
            ),

        "messages":
            messages,
    }


def _active_users_by_slack_id(
    *,
    db: Session,
    workspace_id,
) -> dict[str, User]:
    users = list(
        db.scalars(
            select(User).where(
                User.workspace_id
                == workspace_id,

                User.is_active.is_(
                    True
                ),

                User.slack_user_id.is_not(
                    None
                ),
            )
        )
    )

    return {
        user.slack_user_id:
            user
        for user in users
        if user.slack_user_id
    }


def _unique_valid_mentions(
    *,
    text: str,
    users_by_slack_id: dict[str, User],
) -> list[str]:
    mentions: list[str] = []

    for slack_user_id in (
        SLACK_MENTION_RE.findall(
            text
        )
    ):
        if (
            slack_user_id
            not in users_by_slack_id
        ):
            continue

        if (
            slack_user_id
            not in mentions
        ):
            mentions.append(
                slack_user_id
            )

    return mentions


def _looks_like_assignment_request(
    text: str,
) -> bool:
    return any(
        marker in text
        for marker
        in ASSIGNMENT_MARKERS
    )


def _looks_like_self_commitment(
    text: str,
) -> bool:
    return any(
        marker in text
        for marker
        in SELF_COMMITMENT_MARKERS
    )


def _normalize_name(
    value: str,
) -> str:
    return (
        value
        .replace(
            " ",
            ""
        )
        .replace(
            "　",
            ""
        )
        .strip()
    )


def _name_aliases(
    display_name: str,
) -> set[str]:
    aliases: set[str] = set()

    normalized = _normalize_name(
        display_name
    )

    if len(normalized) >= 2:
        aliases.add(
            normalized
        )

    parts = [
        part.strip()
        for part
        in re.split(
            r"[\s　]+",
            display_name
        )
        if part.strip()
    ]

    for part in parts:
        if len(part) >= 2:
            aliases.add(
                part
            )

    return aliases


def _find_named_assignees(
    *,
    text: str,
    users_by_slack_id: dict[str, User],
) -> list[str]:
    matched_ids: list[str] = []

    normalized_text = (
        _normalize_name(
            text
        )
    )

    alias_to_ids: dict[
        str,
        list[str],
    ] = {}

    for (
        slack_user_id,
        user,
    ) in users_by_slack_id.items():
        for alias in _name_aliases(
            user.display_name
        ):
            alias_to_ids.setdefault(
                alias,
                [],
            ).append(
                slack_user_id
            )

    for (
        alias,
        slack_user_ids,
    ) in alias_to_ids.items():
        # 同じ呼び名の人が複数いる場合は
        # 名前だけでは特定しない
        if len(
            slack_user_ids
        ) != 1:
            continue

        honorific_patterns = (
            f"{alias}さん",
            f"{alias}様",
            f"{alias}くん",
            f"{alias}君",
            f"{alias}ちゃん",
        )

        if not any(
            pattern
            in normalized_text
            for pattern
            in honorific_patterns
        ):
            continue

        slack_user_id = (
            slack_user_ids[0]
        )

        if (
            slack_user_id
            not in matched_ids
        ):
            matched_ids.append(
                slack_user_id
            )

    return matched_ids


def _resolve_assignee(
    *,
    db: Session,
    message: SlackMessage,
    result: TaskDetectionResult,
) -> tuple[
    str | None,
    str,
]:
    if not result.is_task:
        return (
            None,
            "NOT_TASK",
        )

    users_by_slack_id = (
        _active_users_by_slack_id(
            db=db,
            workspace_id=(
                message.workspace_id
            ),
        )
    )

    text = (
        message.text
        or ""
    ).strip()

    mentions = (
        _unique_valid_mentions(
            text=text,
            users_by_slack_id=(
                users_by_slack_id
            ),
        )
    )

    # 複数人が明示されている場合、
    # 現在は単一Ownerしか持てないため
    # 勝手に1人を選ばない
    if (
        len(mentions) > 1
        and
        _looks_like_assignment_request(
            text
        )
    ):
        return (
            None,
            "MULTIPLE_MENTIONS",
        )

    # 1人だけ明示メンションされ、
    # その文章が依頼表現なら最優先
    if (
        len(mentions) == 1
        and
        _looks_like_assignment_request(
            text
        )
    ):
        return (
            mentions[0],
            "DIRECT_MENTION",
        )

    named_assignees = (
        _find_named_assignees(
            text=text,
            users_by_slack_id=(
                users_by_slack_id
            ),
        )
    )

    # 名前指定が複数人なら
    # 単一担当者を選ばない
    if (
        len(named_assignees) > 1
        and
        _looks_like_assignment_request(
            text
        )
    ):
        return (
            None,
            "MULTIPLE_NAMES",
        )

    if (
        len(named_assignees) == 1
        and
        _looks_like_assignment_request(
            text
        )
    ):
        return (
            named_assignees[0],
            "DIRECT_NAME",
        )

    # 「僕がやります」
    # 「確認します」
    # 「対応しておきます」
    # などの明確な自己コミット
    if (
        message.slack_user_id
        and
        message.slack_user_id
        in users_by_slack_id
        and
        _looks_like_self_commitment(
            text
        )
    ):
        return (
            message.slack_user_id,
            "SELF_COMMITMENT",
        )

    # AIが文脈から担当者を出している場合も
    # 実在するSlack User IDか必ず検証する
    ai_assignee = (
        result.assignee_slack_user_id
    )

    if (
        ai_assignee
        and
        ai_assignee
        in users_by_slack_id
    ):
        return (
            ai_assignee,
            "AI_CONTEXT",
        )

    return (
        None,
        "UNRESOLVED",
    )


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

    conversation_context = (
        _get_conversation_context(
            db=db,
            message=message,
        )
    )

    context = {
        "current_datetime_jst":
            now_jst.isoformat(),

        "target_message": {
            "id":
                str(
                    message.id
                ),

            "text":
                message.text,

            "message_ts":
                message.message_ts,

            "thread_ts":
                message.thread_ts,
        },

        "conversation_context":
            conversation_context,

        "sender":
            _get_sender(
                db=db,
                message=message,
            ),

        "channel":
            _get_channel(
                db=db,
                message=message,
            ),

        "workspace_users":
            _get_users(
                db=db,
                workspace_id=(
                    message.workspace_id
                ),
            ),

        "project_candidates":
            _get_projects(
                db=db,
                workspace_id=(
                    message.workspace_id
                ),
            ),
    }

    print(
        "[MIRANOAH CONTEXT] "
        f"message={message.id} "
        f"type="
        f"{conversation_context['context_type']} "
        f"messages="
        f"{conversation_context['message_count']}"
    )

    client = OpenAI(
        api_key=(
            settings.openai_api_key
        )
    )

    response = (
        client.responses.create(
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
                    "type":
                        "json_schema",

                    "name":
                        "miranoah_task_detection",

                    "strict":
                        True,

                    "schema":
                        TASK_DETECTION_SCHEMA,
                }
            },

            store=False,
        )
    )

    if not response.output_text:
        raise RuntimeError(
            "OpenAI returned empty output."
        )

    parsed = json.loads(
        response.output_text
    )

    result = (
        TaskDetectionResult
        .model_validate(
            parsed
        )
    )

    (
        resolved_assignee,
        assignee_source,
    ) = _resolve_assignee(
        db=db,
        message=message,
        result=result,
    )

    result = result.model_copy(
        update={
            "assignee_slack_user_id":
                resolved_assignee,
        }
    )

    print(
        "[MIRANOAH ASSIGNEE] "
        f"message={message.id} "
        f"assignee="
        f"{resolved_assignee} "
        f"source="
        f"{assignee_source}"
    )

    return result
