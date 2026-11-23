# =============================================================================
# app/routers/auth.py  —  AUTHENTICATION ENDPOINTS
# =============================================================================
# This router handles everything related to user identity:
#   POST /api/auth/signup/jobseeker  → register as a job seeker
#   POST /api/auth/signup/recruiter  → register as a recruiter
#   POST /api/auth/upgrade/recruiter → add recruiter role to existing job seeker
#   POST /api/auth/login             → authenticate and get tokens
#   POST /api/auth/logout            → clear auth cookies
#   POST /api/auth/refresh           → exchange refresh token for new tokens
#   GET  /api/auth/me                → get current user info
#
# LEARNING CONCEPT ► Router = Group of Related Endpoints
#   An `APIRouter` is a mini-application that holds related routes.
#   `app.include_router(auth.router, prefix="/api/auth")` mounts it at the prefix.
#
# LEARNING CONCEPT ► Separation of Concerns
#   The router is intentionally thin — it only:
#     1. Validates input (via Pydantic schemas)
#     2. Calls the service layer
#     3. Sets cookies and returns a response
#   All business logic lives in `auth_service.py`.
# =============================================================================

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

# `APIRouter()` creates a router instance.  All `@router.get/post/...`
# decorators below register endpoints on this router.
router = APIRouter()

# =============================================================================
# SIGNUP ENDPOINTS
# =============================================================================


@router.post("/signup/jobseeker", status_code=201)
async def signup_job_seeker(
    body: SignupSchema,         # FastAPI parses + validates the JSON body
    response: Response,         # FastAPI injects this for us to set cookies
    db: AsyncSession = Depends(get_db),  # dependency injection: DB session
):
    """
    Register a new job seeker account.
    Returns 201 Created on success.

    LEARNING NOTE ► status_code=201
      By default FastAPI returns 200.  For resource creation, 201 (Created)
      is semantically more accurate.

    FLOW:
      1. Pydantic validates body (email format, password length, name not empty)
      2. auth_service creates the user + profile in the database
      3. auth_service generates access + refresh JWT tokens
      4. We set both tokens as httpOnly cookies
      5. Return a success message
    """
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
    """Register a new recruiter account with company details."""
    tokens = await auth_service.signup_recruiter(db, body)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Recruiter account created successfully"}


@router.post("/upgrade/recruiter")
async def upgrade_to_recruiter(
    body: RecruiterSignupSchema,
    response: Response,
    # `Depends(authorize_roles("JOB_SEEKER"))` → only job seekers can upgrade.
    # FastAPI first calls `require_auth` (via authorize_roles) to validate the
    # JWT, then checks the role.  `auth` receives the decoded JWT payload.
    auth: Annotated[dict, Depends(authorize_roles("JOB_SEEKER"))],
    db: AsyncSession = Depends(get_db),
):
    """
    Add the RECRUITER role to an existing JOB_SEEKER account.
    Issues new tokens that include both roles.

    LEARNING NOTE ► why new tokens?
      The JWT payload includes the user's roles.  After upgrading, the old
      access token still says ["JOB_SEEKER"].  We issue new tokens with
      ["JOB_SEEKER", "RECRUITER"] so the user gets immediate access.
    """
    result = await auth_service.upgrade_to_recruiter(db, auth["userId"], body)
    set_access_token_cookie(response, result["tokens"]["accessToken"])
    set_refresh_token_cookie(response, result["tokens"]["refreshToken"])
    user_data = await auth_service.get_current_user(db, auth["userId"])
    return {"user": user_data}


# =============================================================================
# LOGIN / LOGOUT
# =============================================================================


@router.post("/login")
async def login(
    body: LoginSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email + password.
    Sets httpOnly cookies on success.

    LEARNING NOTE ► we don't return the tokens in the response body.
    Sending them as cookies (httpOnly) prevents JavaScript from accessing
    them, protecting against XSS attacks.
    """
    tokens = await auth_service.login(db, body.email, body.password)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Logged in successfully"}


@router.post("/logout")
async def logout(response: Response):
    """
    Clear both auth cookies.
    No DB operation needed — JWTs are stateless.

    LEARNING NOTE ► stateless logout trade-off
      The JWT is still cryptographically valid until it expires (15 min).
      True token invalidation requires a "denylist" in Redis — not implemented
      here (the Node.js original doesn't either).  Clearing the cookie is
      sufficient for browser clients.
    """
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Use the refresh token cookie to get new access + refresh tokens.
    Called automatically by the frontend when the access token expires.

    FLOW:
      1. Read the `refreshToken` cookie from the incoming request.
      2. Verify it's a valid, unexpired refresh token.
      3. Issue new access + refresh tokens (rotation: old refresh invalidated).
      4. Set new cookies.

    LEARNING NOTE ► token rotation
      We issue a new refresh token on every refresh.  This means a stolen
      refresh token can only be used ONCE before it's replaced.  The legitimate
      client will get a 401 on the next refresh, alerting them to log in again.
    """
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        from app.errors.app_error import AppError
        raise AppError("Missing refresh token", 401)

    tokens = await auth_service.refresh_tokens(db, refresh_token)
    set_access_token_cookie(response, tokens["accessToken"])
    set_refresh_token_cookie(response, tokens["refreshToken"])
    return {"message": "Tokens refreshed"}


# =============================================================================
# CURRENT USER
# =============================================================================


@router.get("/me")
async def get_me(
    auth: Annotated[dict, Depends(require_auth)],  # validates JWT + extracts userId
    db: AsyncSession = Depends(get_db),
):
    """
    Return the current authenticated user's info.
    Used by the frontend to populate the user profile UI.

    LEARNING NOTE ► `auth["userId"]` comes from the JWT payload.
      No session store lookup needed — the token already carries the user ID.
      We only hit the DB to fetch fresh data (name, email, roles, is_active).
    """
    user_data = await auth_service.get_current_user(db, auth["userId"])
    return {"user": user_data}
