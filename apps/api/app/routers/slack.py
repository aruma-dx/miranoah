import json
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.security import verify_slack_signature
from app.schemas.slack import SlackEventEnvelope
from app.services.queue import (
    enqueue_slack_action,
    enqueue_slack_event,
)


router = APIRouter(
    prefix="/api/v1/slack",
    tags=["slack"],
)


def _verify_request_signature(
    request: Request,
    body: bytes,
) -> None:
    if settings.app_env == "development":
        return

    valid = verify_slack_signature(
        signing_secret=settings.slack_signing_secret,
        timestamp=request.headers.get(
            "x-slack-request-timestamp"
        ),
        signature=request.headers.get(
            "x-slack-signature"
        ),
        body=body,
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid Slack signature",
        )


@router.post("/events")
async def slack_events(
    request: Request,
):
    body = await request.body()

    _verify_request_signature(
        request=request,
        body=body,
    )

    try:
        raw_payload = json.loads(body)

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        ) from exc

    try:
        payload = (
            SlackEventEnvelope.model_validate(
                raw_payload
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid Slack event payload",
        ) from exc

    if payload.type == "url_verification":
        return {
            "challenge": payload.challenge,
        }

    event = payload.event or {}

    # MIRANOAH policy:
    # Slack DM ingestion is excluded.
    if event.get("channel_type") == "im":
        return {
            "ok": True,
            "ignored": True,
            "reason": "dm_excluded",
        }

    queue_payload = payload.model_dump(
        mode="json"
    )

    retry_num = request.headers.get(
        "x-slack-retry-num"
    )

    retry_reason = request.headers.get(
        "x-slack-retry-reason"
    )

    if retry_num is not None:
        queue_payload[
            "_miranoah_retry_num"
        ] = retry_num

    if retry_reason is not None:
        queue_payload[
            "_miranoah_retry_reason"
        ] = retry_reason

    enqueue_slack_event(
        queue_payload
    )

    return {
        "ok": True,
        "queued": True,
        "retry": retry_num is not None,
    }


@router.post("/actions")
async def slack_actions(
    request: Request,
):
    body = await request.body()

    _verify_request_signature(
        request=request,
        body=body,
    )

    try:
        form_data = parse_qs(
            body.decode("utf-8")
        )

    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid Slack action encoding",
        ) from exc

    payload_values = form_data.get(
        "payload"
    )

    if not payload_values:
        raise HTTPException(
            status_code=400,
            detail="Slack action payload is missing",
        )

    try:
        payload = json.loads(
            payload_values[0]
        )

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid Slack action JSON",
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Slack action payload",
        )

    action_type = payload.get(
        "type"
    )

    if action_type not in {
        "block_actions",
        "view_submission",
        "view_closed",
        "shortcut",
        "message_action",
    }:
        return {
            "ok": True,
            "ignored": True,
            "reason": "unsupported_action_type",
        }

    enqueue_slack_action(
        payload
    )

    # Slack requires interactive requests
    # to be acknowledged very quickly.
    # Actual processing happens in Worker.
    return {
        "ok": True,
        "queued": True,
    }
