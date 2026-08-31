import json
from fastapi import APIRouter, HTTPException, Request
from app.core.config import settings
from app.core.security import verify_slack_signature
from app.schemas.slack import SlackEventEnvelope
from app.services.queue import enqueue_slack_event

router = APIRouter(prefix="/api/v1/slack", tags=["slack"])


@router.post("/events")
async def slack_events(request: Request):
    body = await request.body()
    if settings.app_env != "development":
        valid = verify_slack_signature(
            signing_secret=settings.slack_signing_secret,
            timestamp=request.headers.get("x-slack-request-timestamp"),
            signature=request.headers.get("x-slack-signature"),
            body=body,
        )
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload = SlackEventEnvelope.model_validate(json.loads(body))
    if payload.type == "url_verification":
        return {"challenge": payload.challenge}

    # DM ingestion is intentionally excluded by policy. The worker also re-checks this.
    event = payload.event or {}
    if event.get("channel_type") == "im":
        return {"ok": True, "ignored": True}

    enqueue_slack_event(payload.model_dump(mode="json"))
    return {"ok": True, "queued": True}
