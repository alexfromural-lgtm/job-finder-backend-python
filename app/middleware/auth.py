# =============================================================================
# app/middleware/auth.py  —  AUTHENTICATION & AUTHORIZATION DEPENDENCIES
# =============================================================================
# FastAPI uses a "dependency injection" system: functions decorated with
# `Depends(...)` are called automatically before the route handler runs.
#
# This module provides two such dependencies:
#   • `require_auth`     – verifies the user is logged in (valid JWT cookie)
#   • `authorize_roles`  – factory that checks the user has a specific role
#
# LEARNING CONCEPT ► Dependency Injection in FastAPI
#   Traditional middleware runs for EVERY request (even public routes).
#   FastAPI dependencies are opt-in per-route — only protected routes pay the
#   authentication cost.
#
#   EXAMPLE:
#     @router.get("/profile")
#     async def get_profile(auth: Annotated[dict, Depends(require_auth)]):
#         # `auth` is the decoded JWT payload: {"userId": "...", "roles": [...]}
#         return {"user_id": auth["userId"]}
#
# LEARNING CONCEPT ► Annotated type hints
#   `Annotated[dict, Depends(require_auth)]` combines:
#     • the type hint (dict) for IDE completion
#     • the dependency instruction (Depends) for FastAPI
# =============================================================================

from typing import Annotated

from fastapi import Depends, Request

from app.errors.app_error import AppError
from app.utils.token import verify_access_token


# =============================================================================
# HELPER: extract JWT from cookie
# =============================================================================
# Auth tokens are stored as httpOnly cookies (not in localStorage) for XSS
# protection.  The browser automatically sends them with every request.
#
# LEARNING NOTE ► httpOnly cookies:
#   JavaScript cannot read httpOnly cookies (document.cookie won't see them).
#   This prevents XSS attacks from stealing tokens.
#   The downside: SPAs must handle auth differently than with localStorage.
# =============================================================================
def _get_token_from_cookie(request: Request) -> str:
    """Extract accessToken cookie — raises 401 if missing."""
    token = request.cookies.get("accessToken")  # reads the browser cookie
    if not token:
        raise AppError("Missing access token", 401)
    return token


# =============================================================================
# DEPENDENCY 1: require_auth
# =============================================================================
# 1. Reads the `accessToken` cookie from the HTTP request.
# 2. Calls `verify_access_token` which decodes + validates the JWT signature
#    and expiry.  Raises AppError(401) on failure.
# 3. Returns the decoded payload dict:
#    { "userId": "uuid", "roles": ["JOB_SEEKER"], "exp": 1234567890 }
#
# USAGE IN A ROUTE:
#   @router.get("/me")
#   async def me(auth: Annotated[dict, Depends(require_auth)]):
#       return {"id": auth["userId"]}
# =============================================================================
def require_auth(request: Request) -> dict:
    """
    FastAPI dependency that validates the accessToken cookie and
    returns the decoded JWT payload (userId, roles).

    Mirrors the requireAuth middleware in auth.middleware.ts.
    Use with: auth_data: Annotated[dict, Depends(require_auth)]
    """
    token = _get_token_from_cookie(request)
    # verify_access_token raises AppError(401) on failure
    return verify_access_token(token)


# =============================================================================
# DEPENDENCY 2: authorize_roles  (factory function)
# =============================================================================
# `authorize_roles` is a FACTORY — it returns a dependency function.
# This pattern lets us parameterise the dependency:
#
#   Depends(authorize_roles("RECRUITER"))   # only recruiters
#   Depends(authorize_roles("ADMIN"))       # only admins
#   Depends(authorize_roles("JOB_SEEKER", "ADMIN"))  # either role
#
# HOW IT WORKS:
#   authorize_roles("RECRUITER")  → returns _check
#   FastAPI calls _check(auth=<result of require_auth>)
#   _check inspects auth["roles"] and raises 403 if none match.
#
# LEARNING EXAMPLE ► using as a route dependency (no value needed):
#   @router.post("/job", dependencies=[Depends(authorize_roles("RECRUITER"))])
#   async def create_job(...): ...
#
#   Or inject the payload too:
#   @router.get("/dashboard")
#   async def dash(auth: Annotated[dict, Depends(authorize_roles("RECRUITER"))]):
#       recruiter_id = auth["userId"]
# =============================================================================
def authorize_roles(*allowed_roles: str):
    """
    FastAPI dependency factory — checks that the current user holds at
    least one of the allowed roles.

    Mirrors authorizeRoles() in auth.middleware.ts.

    Usage:
        @router.get("/", dependencies=[Depends(authorize_roles("RECRUITER"))])
        # OR inject into path function:
        def endpoint(auth: Annotated[dict, Depends(require_auth)],
                     _: Annotated[None, Depends(authorize_roles("RECRUITER"))]):
    """

    def _check(auth: Annotated[dict, Depends(require_auth)]) -> dict:
        # auth["roles"] is a list like ["JOB_SEEKER"] or ["JOB_SEEKER", "RECRUITER"]
        user_roles: list[str] = auth.get("roles", [])
        # `any(...)` returns True if at least one allowed_role is in user_roles.
        if not any(role in user_roles for role in allowed_roles):
            raise AppError("Access denied.", 403)
        return auth

    return _check
