from __future__ import annotations

import secrets

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SESSION_EXPIRE_HOURS,
    create_session_token,
    decode_session_token,
)
from app.db.session import get_db
from app.models.core import User
from app.services.google_auth import (
    GoogleAuthError,
    build_google_authorization_url,
    exchange_code_for_tokens,
    get_google_userinfo,
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


def _secure_cookie() -> bool:
    return (
        settings.app_env
        != "development"
    )


@router.get("/google/login")
def google_login():
    state = secrets.token_urlsafe(32)

    authorization_url = (
        build_google_authorization_url(
            state=state
        )
    )

    response = RedirectResponse(
        url=authorization_url,
        status_code=302,
    )

    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        max_age=600,
        path="/",
    )

    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(
            status_code=401,
            detail=(
                f"Google login failed: {error}"
            ),
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google authorization code "
                "is missing."
            ),
        )

    expected_state = request.cookies.get(
        OAUTH_STATE_COOKIE_NAME
    )

    if (
        not state
        or not expected_state
        or not secrets.compare_digest(
            state,
            expected_state,
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state.",
        )

    try:
        token_payload = (
            await exchange_code_for_tokens(
                code=code
            )
        )

        access_token = token_payload[
            "access_token"
        ]

        google_user = (
            await get_google_userinfo(
                access_token=access_token
            )
        )

    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc

    email = (
        google_user["email"]
        .strip()
        .lower()
    )

    users = db.scalars(
        select(User).where(
            func.lower(User.email)
            == email,
            User.is_active.is_(True),
        )
    ).all()

    if not users:
        raise HTTPException(
            status_code=403,
            detail=(
                "このGoogleアカウントに対応する"
                "MIRANOAHユーザーがありません。"
            ),
        )

    if len(users) > 1:
        raise HTTPException(
            status_code=409,
            detail=(
                "同じメールアドレスを持つ"
                "MIRANOAHユーザーが複数存在します。"
            ),
        )

    user = users[0]

    session_token = (
        create_session_token(
            user_id=str(user.id),
            workspace_id=str(
                user.workspace_id
            ),
            email=email,
            workspace_role=(
                user.workspace_role.value
            ),
        )
    )

    response = RedirectResponse(
        url=(
            f"{settings.app_base_url}"
            "?login=success"
        ),
        status_code=302,
    )

    response.delete_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        path="/",
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        max_age=(
            SESSION_EXPIRE_HOURS
            * 60
            * 60
        ),
        path="/",
    )

    return response


@router.get("/me")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
        )

    payload = decode_session_token(
        token
    )

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid session.",
        )

    user_id = payload.get("sub")

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User is not active.",
        )

    return {
        "id": str(user.id),
        "workspace_id": str(
            user.workspace_id
        ),
        "slack_user_id": (
            user.slack_user_id
        ),
        "email": user.email,
        "display_name": (
            user.display_name
        ),
        "workspace_role": (
            user.workspace_role.value
        ),
        "is_workspace_owner": (
            user.is_workspace_owner
        ),
        "is_active": user.is_active,
    }


@router.post("/logout")
def logout():
    response = {
        "ok": True
    }

    from fastapi.responses import JSONResponse

    result = JSONResponse(
        content=response
    )

    result.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    return result
