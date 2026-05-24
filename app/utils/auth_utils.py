from fastapi import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors.app_error import AppError
from app.models.user import User
from app.utils.token import generate_access_token, generate_refresh_token


async def check_user_exists_by_email(db: AsyncSession, email: str) -> None:
    """
    Raises AppError(409) if a user with that email already exists.
    Mirrors checkUserExistsByEmail() in utils/auth.utils.ts.
    """
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise AppError("User already exists", 409)


def generate_tokens_for_user(user_id: str, roles: list[str]) -> dict:
    """
    Generate access + refresh JWT pair.
    Mirrors generateTokensForUser() in utils/auth.utils.ts.
    """
    access_token = generate_access_token(user_id, roles)
    refresh_token = generate_refresh_token(user_id, roles)
    return {"accessToken": access_token, "refreshToken": refresh_token}


def set_access_token_cookie(response: Response, access_token: str) -> None:
    """
    Set the access token as an httpOnly cookie.
    Mirrors setAccessTokenCookie() in utils/auth.utils.ts.
    """
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=settings.ACCESS_TOKEN_MAX_AGE_MS // 1000,  # FastAPI takes seconds
    )


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
        max_age=settings.REFRESH_TOKEN_MAX_AGE_MS // 1000,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies on logout."""
    response.delete_cookie(key="accessToken", path="/")
    response.delete_cookie(key="refreshToken", path="/")
