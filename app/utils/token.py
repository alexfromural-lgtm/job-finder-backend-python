# =============================================================================
# app/utils/token.py  —  JWT GENERATION AND VERIFICATION
# =============================================================================
# JSON Web Tokens (JWT) are the standard for stateless authentication.
# A JWT is a base64-encoded string with three parts:
#   HEADER.PAYLOAD.SIGNATURE
#
# LEARNING CONCEPT ► How JWT works
#   1. User logs in with email + password.
#   2. Server verifies credentials, then calls `generate_access_token`.
#   3. Server sends the JWT to the client (here: as an httpOnly cookie).
#   4. Client sends the cookie with every future request.
#   5. Server calls `verify_access_token` — no DB lookup needed!
#      The signature proves the token was issued by us and not tampered with.
#
# LEARNING CONCEPT ► Access Token vs Refresh Token
#   Access Token  – Short-lived (15 minutes).  Used to authenticate requests.
#   Refresh Token – Long-lived (7 days).  Only used to get a new access token.
#   Why two tokens? If an access token is stolen, it expires quickly.
#   The refresh token is stored in a stricter httpOnly cookie path.
#
# LIBRARY: `python-jose` — JWT encode/decode with HS256 (HMAC-SHA256).
# =============================================================================

from datetime import datetime, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings
from app.errors.app_error import AppError


# =============================================================================
# HELPER: current UTC time
# =============================================================================
# Always use UTC for token timestamps — avoids timezone confusion between
# servers in different regions.
# =============================================================================
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# generate_access_token
# =============================================================================
# Creates a JWT payload and signs it with the ACCESS_TOKEN_SECRET.
#
# PAYLOAD FIELDS:
#   userId  – who this token belongs to
#   roles   – what the user is allowed to do
#   exp     – Unix timestamp when the token expires (seconds since 1970-01-01)
#   iat     – Unix timestamp when the token was issued ("issued at")
#   type    – "access" (guards against using a refresh token as an access token)
#
# LEARNING EXAMPLE ► decode the JWT manually (at jwt.io):
#   Header:  { "alg": "HS256", "typ": "JWT" }
#   Payload: { "userId": "abc", "roles": ["JOB_SEEKER"], "exp": 1234567890 }
#   Signature: HMAC-SHA256(base64(header)+"."+base64(payload), secret)
# =============================================================================
def generate_access_token(user_id: str, roles: list[str]) -> str:
    """
    Create a short-lived access JWT.
    Mirrors generateAccessToken() in utils/token.ts.
    """
    expire = _now_utc().timestamp() + settings.access_token_expire_seconds
    payload = {
        "userId": user_id,
        "roles": roles,
        "exp": int(expire),   # jose library reads this to check expiry
        "iat": int(_now_utc().timestamp()),
        "type": "access",
    }
    # jwt.encode(payload, secret, algorithm) → signed JWT string
    return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")


# =============================================================================
# generate_refresh_token
# =============================================================================
# Same structure as access token but:
#   • Lives longer (7 days instead of 15 minutes)
#   • Signed with a DIFFERENT secret (so a compromised access secret
#     can't be used to forge refresh tokens)
#   • type="refresh" (prevents using it where an access token is expected)
# =============================================================================
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


# =============================================================================
# verify_access_token
# =============================================================================
# 1. `jwt.decode` checks the signature (was it signed with our secret?) and
#    the `exp` claim (is it still valid?).
# 2. We additionally check `type == "access"` to prevent refresh tokens from
#    being used as access tokens.
# 3. On any error (bad signature, expired, wrong type), we raise AppError(401).
#
# LEARNING NOTE ► JWTError
#   `jose.JWTError` covers: expired token, invalid signature, malformed JWT.
#   We catch it and re-raise as AppError so the global handler sends HTTP 401.
# =============================================================================
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


# =============================================================================
# verify_refresh_token
# =============================================================================
# Same as verify_access_token but uses the REFRESH secret and checks
# type == "refresh".  Called only by the /auth/refresh endpoint.
# =============================================================================
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
