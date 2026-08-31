from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings


class SlackAPIError(RuntimeError):
    pass


class SlackAPIClient:
    BASE_URL = "https://slack.com/api"

    def __init__(self, token: str | None = None):
        self.token = token or settings.slack_bot_token

        if not self.token:
            raise SlackAPIError("SLACK_BOT_TOKEN is not configured.")

    def get(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = urlencode(
            {
                key: value
                for key, value in (params or {}).items()
                if value is not None
            }
        )

        url = f"{self.BASE_URL}/{method}"

        if query:
            url = f"{url}?{query}"

        request = Request(
            url=url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "MIRANOAH/0.1",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")

        except HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise SlackAPIError(
                f"Slack API HTTP error: {exc.code} {body}"
            ) from exc

        except URLError as exc:
            raise SlackAPIError(
                f"Could not connect to Slack API: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(body)

        except json.JSONDecodeError as exc:
            raise SlackAPIError(
                "Slack API returned invalid JSON."
            ) from exc

        if not payload.get("ok"):
            error = payload.get(
                "error",
                "unknown_error",
            )

            raise SlackAPIError(
                f"Slack API error on {method}: {error}"
            )

        return payload

    def auth_test(self) -> dict[str, Any]:
        return self.get("auth.test")

    def users_list(
        self,
        cursor: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        return self.get(
            "users.list",
            {
                "limit": limit,
                "cursor": cursor,
            },
        )

    def conversations_list(
        self,
        cursor: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        return self.get(
            "conversations.list",
            {
                "limit": limit,
                "cursor": cursor,
                "exclude_archived": "false",
                "types": "public_channel,private_channel",
            },
        )
