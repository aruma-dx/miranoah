from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings


GOOGLE_AUTHORIZATION_ENDPOINT = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

GOOGLE_TOKEN_ENDPOINT = (
    "https://oauth2.googleapis.com/token"
)

GOOGLE_USERINFO_ENDPOINT = (
    "https://openidconnect.googleapis.com/v1/userinfo"
)


class GoogleAuthError(RuntimeError):
    pass


def build_google_authorization_url(
    *,
    state: str,
) -> str:
    if not settings.google_client_id:
        raise GoogleAuthError(
            "GOOGLE_CLIENT_ID is not configured."
        )

    if not settings.google_redirect_uri:
        raise GoogleAuthError(
            "GOOGLE_REDIRECT_URI is not configured."
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "include_granted_scopes": "true",
    }

    return (
        GOOGLE_AUTHORIZATION_ENDPOINT
        + "?"
        + urlencode(params)
    )


async def exchange_code_for_tokens(
    *,
    code: str,
) -> dict[str, Any]:
    if not settings.google_client_id:
        raise GoogleAuthError(
            "GOOGLE_CLIENT_ID is not configured."
        )

    if not settings.google_client_secret:
        raise GoogleAuthError(
            "GOOGLE_CLIENT_SECRET is not configured."
        )

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:
        response = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )

    if response.status_code != 200:
        raise GoogleAuthError(
            "Google token exchange failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    payload = response.json()

    access_token = payload.get(
        "access_token"
    )

    if not access_token:
        raise GoogleAuthError(
            "Google did not return an access token."
        )

    return payload


async def get_google_userinfo(
    *,
    access_token: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:
        response = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={
                "Authorization": (
                    f"Bearer {access_token}"
                )
            },
        )

    if response.status_code != 200:
        raise GoogleAuthError(
            "Google userinfo request failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    payload = response.json()

    email = payload.get("email")

    if not email:
        raise GoogleAuthError(
            "Google account has no email."
        )

    if payload.get("email_verified") is not True:
        raise GoogleAuthError(
            "Google email is not verified."
        )

    return payload
