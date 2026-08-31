import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


SESSION_COOKIE_NAME = "miranoah_session"
OAUTH_STATE_COOKIE_NAME = "miranoah_oauth_state"

SESSION_ALGORITHM = "HS256"
SESSION_EXPIRE_HOURS = 12


def verify_slack_signature(
    *,
    signing_secret: str,
    timestamp: str | None,
    signature: str | None,
    body: bytes,
) -> bool:
    if not signing_secret or not timestamp or not signature:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - ts) > 60 * 5:
        return False

    base = f"v0:{timestamp}:".encode() + body

    expected = (
        "v0="
        + hmac.new(
            signing_secret.encode(),
            base,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(
        expected,
        signature,
    )


def create_session_token(
    *,
    user_id: str,
    workspace_id: str,
    email: str,
    workspace_role: str,
) -> str:
    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        hours=SESSION_EXPIRE_HOURS
    )

    payload = {
        "sub": user_id,
        "workspace_id": workspace_id,
        "email": email,
        "workspace_role": workspace_role,
        "type": "session",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=SESSION_ALGORITHM,
    )


def decode_session_token(
    token: str,
) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[SESSION_ALGORITHM],
        )

    except JWTError:
        return None

    if payload.get("type") != "session":
        return None

    if not payload.get("sub"):
        return None

    return payload
