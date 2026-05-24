from typing import Annotated

from fastapi import Depends, Request

from app.errors.app_error import AppError
from app.utils.token import verify_access_token


def _get_token_from_cookie(request: Request) -> str:
    """Extract accessToken cookie — raises 401 if missing."""
    token = request.cookies.get("accessToken")
    if not token:
        raise AppError("Missing access token", 401)
    return token


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
        user_roles: list[str] = auth.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise AppError("Access denied.", 403)
        return auth

    return _check
