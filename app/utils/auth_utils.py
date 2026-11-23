# =============================================================================
# app/utils/auth_utils.py  —  AUTH COOKIE HELPERS
# =============================================================================
# These helpers set, read, and clear the two httpOnly cookies that carry JWTs.
# They are shared by the auth router (login, signup, refresh, logout).
#
# LEARNING CONCEPT ► Why httpOnly Cookies for JWT?
#   Option A: Store JWT in localStorage / sessionStorage
#     ✓ Easy to implement
#     ✗ Vulnerable to XSS — any injected script can steal it
#
#   Option B: Store JWT in httpOnly cookie  (this project)
#     ✓ JavaScript cannot read httpOnly cookies → XSS-safe
#     ✓ Browser sends them automatically with every request
#     ✗ Must handle CSRF (mitigated here with SameSite + CORS)
#
# LEARNING CONCEPT ► Cookie Security Flags
#   httponly  – JS cannot read the cookie (XSS protection)
#   secure    – browser only sends over HTTPS (not plain HTTP)
#   samesite  – controls cross-site cookie sending:
#               "lax"    – allows top-level navigation (safe default)
#               "strict" – never sent cross-site (more restrictive)
#               "none"   – always sent (requires secure=True)
# =============================================================================

from fastapi import Response
from app.config import settings


# =============================================================================
# set_access_token_cookie
# =============================================================================
# Sets the `accessToken` cookie with:
#   • httponly=True   → JS cannot steal it via XSS
#   • secure=True     → only sent over HTTPS (production only)
#   • samesite="lax"  → allowed on same-site navigation, blocked on cross-site
#   • max_age=900     → 15 minutes (derived from ACCESS_TOKEN_EXPIRES_IN)
#   • path="/"        → sent with every request (not just specific paths)
#
# LEARNING NOTE ► max_age vs expires
#   `max_age` (seconds from now) is preferred over `expires` (absolute date)
#   because it doesn't depend on the client's clock being correct.
# =============================================================================
def set_access_token_cookie(response: Response, access_token: str) -> None:
    """
    Set the access token as an httpOnly cookie.
    Mirrors setAccessTokenCookie() in utils/auth.utils.ts.
    """
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        secure=settings.is_production,   # only True in production (HTTPS)
        samesite="lax",
        path="/",
        max_age=settings.access_token_expire_seconds,  # e.g. 900 seconds (15 min)
    )


# =============================================================================
# set_refresh_token_cookie
# =============================================================================
# Same as the access token cookie but:
#   • max_age matches the refresh token lifetime (e.g. 7 days = 604800 seconds)
#   • REFRESH_TOKEN_MAX_AGE_MS is stored in milliseconds in .env to match the
#     Node.js convention — we divide by 1000 to get seconds for the cookie.
#
# LEARNING NOTE ► why a separate refresh token cookie?
#   The refresh token only needs to reach /api/auth/refresh, so ideally it
#   would use path="/api/auth/refresh" (narrower scope).  Here it uses path="/"
#   to keep things simple, matching the Node.js behaviour.
# =============================================================================
def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    """
    Set the refresh token as an httpOnly cookie.
    Mirrors setRefreshTokenCookie() in utils/auth.utils.ts.
    """
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=settings.REFRESH_TOKEN_MAX_AGE_MS // 1000,  # ms → seconds
    )


# =============================================================================
# clear_auth_cookies
# =============================================================================
# `delete_cookie` tells the browser to expire the cookie immediately by setting
# its max_age to 0 (or a date in the past).
#
# LEARNING NOTE ► why both cookies?
#   After logout, we clear BOTH tokens so the user must log in again even if
#   they intercept the refresh token before it expires.
#
# USAGE IN LOGOUT ROUTE:
#   @router.post("/logout")
#   async def logout(response: Response):
#       clear_auth_cookies(response)
#       return {"message": "Logged out successfully"}
# =============================================================================
def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies on logout."""
    response.delete_cookie(key="accessToken",  path="/")
    response.delete_cookie(key="refreshToken", path="/")
