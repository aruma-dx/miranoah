import json

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.security import verify_slack_signature
from app.schemas.slack import SlackEventEnvelope
from app.services.queue import enqueue_slack_event


router = APIRouter(
    prefix="/api/v1/slack",
    tags=["slack"],
)


@router.post("/events")
async def slack_events(request: Request):
    body = await request.body()

    if settings.app_env != "development":
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

    try:
        raw_payload = json.loads(body)

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        ) from exc

    try:
        payload = SlackEventEnvelope.model_validate(
            raw_payload
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid Slack event payload",
        ) from exc

    if payload.type == "url_verification":
        return {
            "challenge": payload.challenge
        }

    event = payload.event or {}

    # MIRANOAH policy:
    # Slack DM is intentionally not ingested.
    if event.get("channel_type") == "im":
        return {
            "ok": True,
            "ignored": True,
            "reason": "dm_excluded",
        }

    queue_payload = payload.model_dump(
        mode="json"
    )

    # Slack retry information is preserved.
    # We still enqueue retries because the worker is idempotent.
    # This avoids losing an event if Slack retried because the
    # first delivery was interrupted before persistence.
    retry_num = request.headers.get(
        "x-slack-retry-num"
    )
    retry_reason = request.headers.get(
        "x-slack-retry-reason"
    )

    if retry_num is not None:
        queue_payload["_miranoah_retry_num"] = (
            retry_num
        )

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
