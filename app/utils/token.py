from datetime import datetime, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings
from app.errors.app_error import AppError


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_access_token(user_id: str, roles: list[str]) -> str:
    """
    Create a short-lived access JWT.
    Mirrors generateAccessToken() in utils/token.ts.
    """
    expire = _now_utc().timestamp() + settings.access_token_expire_seconds
    payload = {
        "userId": user_id,
        "roles": roles,
        "exp": int(expire),
        "iat": int(_now_utc().timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")


def generate_refresh_token(user_id: str, roles: list[str]) -> str:
    """
    Create a long-lived refresh JWT.
    Mirrors generateRefreshToken() in utils/token.ts.
    """
    expire = _now_utc().timestamp() + settings.refresh_token_expire_seconds
    payload = {
        "userId": user_id,
        "roles": roles,
        "exp": int(expire),
        "iat": int(_now_utc().timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm="HS256")


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Raises AppError(401) for expired or invalid tokens.
    Mirrors verifyAccessToken() in utils/token.ts.
    """
    try:
        payload = jwt.decode(token, settings.ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise AppError("Invalid token type", 401)
        return payload
    except JWTError as exc:
        raise AppError(str(exc), 401)


def verify_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.
    Raises AppError(401) for expired or invalid tokens.
    Mirrors verifyRefreshToken() in utils/token.ts.
    """
    try:
        payload = jwt.decode(token, settings.REFRESH_TOKEN_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise AppError("Invalid token type", 401)
        return payload
    except JWTError as exc:
        raise AppError(str(exc), 401)
