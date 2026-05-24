from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.schemas.auth import LoginSchema, SignupSchema
from app.schemas.recruiter import RecruiterSignupSchema
from app.services import auth_service
from app.utils.auth_utils import (
    clear_auth_cookies,
    set_access_token_cookie,
    set_refresh_token_cookie,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Signup endpoints
# Mirrors auth.route.ts signupLimiter (rate limiting applied in main.py via slowapi)
# ---------------------------------------------------------------------------


@router.post("/signup/jobseeker", status_code=201)
async def signup_job_seeker(
    body: SignupSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    tokens = await auth_service.signup_job_seeker(db, body.name, body.email, body.password)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Job seeker account created successfully"}


@router.post("/signup/recruiter", status_code=201)
async def signup_recruiter(
    body: RecruiterSignupSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    tokens = await auth_service.signup_recruiter(db, body)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Recruiter account created successfully"}


@router.post("/upgrade/recruiter")
async def upgrade_to_recruiter(
    body: RecruiterSignupSchema,
    response: Response,
    auth: Annotated[dict, Depends(authorize_roles("JOB_SEEKER"))],
    db: AsyncSession = Depends(get_db),
):
    result = await auth_service.upgrade_to_recruiter(db, auth["userId"], body)
    set_access_token_cookie(response, result["tokens"]["accessToken"])
    set_refresh_token_cookie(response, result["tokens"]["refreshToken"])
    return {"message": "Account upgraded to Recruiter successfully"}


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(
    body: LoginSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    tokens = await auth_service.login(db, body.email, body.password)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Logged in successfully"}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        from app.errors.app_error import AppError
        raise AppError("Missing refresh token", 401)

    tokens = await auth_service.refresh_tokens(db, refresh_token)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Tokens refreshed"}


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_me(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_current_user(db, auth["userId"])
