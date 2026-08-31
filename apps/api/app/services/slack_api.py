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
            raise SlackAPIError(
                "SLACK_BOT_TOKEN is not configured."
            )

    def _request(
        self,
        method: str,
        *,
        http_method: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{method}"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "MIRANOAH/0.1",
        }

        data: bytes | None = None

        if http_method == "GET":
            query = urlencode(
                {
                    key: value
                    for key, value in (params or {}).items()
                    if value is not None
                }
            )

            if query:
                url = f"{url}?{query}"

        elif http_method == "POST":
            headers["Content-Type"] = (
                "application/json; charset=utf-8"
            )

            data = json.dumps(
                json_body or {},
                ensure_ascii=False,
            ).encode("utf-8")

        else:
            raise SlackAPIError(
                f"Unsupported HTTP method: {http_method}"
            )

        request = Request(
            url=url,
            method=http_method,
            headers=headers,
            data=data,
        )

        try:
            with urlopen(
                request,
                timeout=30,
            ) as response:
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

    def get(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            method,
            http_method="GET",
            params=params,
        )

    def post(
        self,
        method: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            method,
            http_method="POST",
            json_body=json_body,
        )

    def auth_test(self) -> dict[str, Any]:
        return self.get(
            "auth.test"
        )

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

    def chat_post_message(
        self,
        *,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media,
        }

        if thread_ts:
            payload["thread_ts"] = thread_ts

        return self.post(
            "chat.postMessage",
            payload,
        )
