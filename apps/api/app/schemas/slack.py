from typing import Any
from pydantic import BaseModel, Field


class SlackEventEnvelope(BaseModel):
    token: str | None = None
    team_id: str | None = None
    api_app_id: str | None = None
    type: str
    event_id: str | None = None
    event_time: int | None = None
    challenge: str | None = None
    event: dict[str, Any] | None = None


class SlackAck(BaseModel):
    ok: bool = True
    queued: bool = False
    ignored: bool = False
