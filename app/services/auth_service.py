# =============================================================================
# app/services/auth_service.py  —  AUTHENTICATION BUSINESS LOGIC
# =============================================================================
# The service layer contains all business logic — the "rules" of the application.
# Routers call services; services talk to the database.
#
# LAYER ARCHITECTURE:
#   HTTP Request → Router (validate input) → Service (business logic) → DB
#   HTTP Response ← Router ← Service ← DB
#
# LEARNING CONCEPT ► Why a Separate Service Layer?
#   Without services, all logic lives in routers.  With services:
#     ✓ Logic can be reused (e.g., apply_to_job is called by both the router
#       AND the Celery worker)
#     ✓ Easier to test (services don't depend on HTTP concepts)
#     ✓ Cleaner code — each file has one responsibility
#
# FUNCTIONS IN THIS FILE:
#   signup_job_seeker   → register + create profile + return tokens
#   signup_recruiter    → register + create company profile + return tokens
#   upgrade_to_recruiter → add recruiter role to existing user
#   login               → verify credentials + return tokens
#   refresh_tokens      → rotate tokens using refresh JWT
#   get_current_user    → load user data by ID
# =============================================================================

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.user import User, Role
from app.models.profiles import JobSeekerProfile, RecruiterProfile
from app.schemas.recruiter import RecruiterSignupSchema
from app.utils.hash import hash_password, compare_passwords
from app.utils.token import generate_access_token, generate_refresh_token, verify_refresh_token


# =============================================================================
# HELPER: generate both tokens for a user
# =============================================================================
# Used by signup, login, and refresh — DRY pattern.
#
# LEARNING NOTE ► roles serialization
#   `user.roles` might contain Role enum values OR plain strings depending on
#   how they were loaded.  `r.value if hasattr(r, "value") else r` handles both:
#     Role.JOB_SEEKER.value → "JOB_SEEKER"
#     "JOB_SEEKER"          → "JOB_SEEKER"  (already a string)
# =============================================================================
def _make_tokens(user: User) -> dict:
    roles = [r.value if hasattr(r, "value") else r for r in user.roles]
    return {
        "accessToken":  generate_access_token(user.id, roles),
        "refreshToken": generate_refresh_token(user.id, roles),
    }


# =============================================================================
# signup_job_seeker
# =============================================================================
# 1. Create a User row with hashed password and JOB_SEEKER role.
# 2. `await db.flush()` sends the INSERT without committing — the user gets
#    an ID but we can still rollback if the profile insert fails.
# 3. Create the JobSeekerProfile linked to the new user.
# 4. `await db.commit()` persists both rows atomically.
# 5. Return tokens.
#
# LEARNING CONCEPT ► flush() vs commit()
#   flush()  → sends SQL to the database but does NOT commit the transaction.
#              Useful when you need the auto-generated ID of a row before
#              creating related rows that reference it.
#   commit() → finalises the transaction — all changes become permanent.
#   rollback() → undoes all changes since the last commit.
# =============================================================================
async def signup_job_seeker(
    db: AsyncSession, name: str, email: str, password: str
) -> dict:
    """
    Register a new job seeker account.
    Returns {"accessToken": "...", "refreshToken": "..."} on success.
    Raises AppError(409) if the email is already registered.
    """
    # Check for duplicate email BEFORE trying to insert.
    # (The DB would catch it via UNIQUE constraint too, but this gives a nicer error.)
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise AppError("Email already registered", 409)

    # Create User with hashed password.
    user = User(
        name=name,
        email=email,
        password=hash_password(password),  # NEVER store plain text!
        roles=[Role.JOB_SEEKER],
    )
    db.add(user)
    await db.flush()   # get user.id before creating the profile

    # Create the associated profile (linked via user_id FK).
    profile = JobSeekerProfile(user_id=user.id)
    db.add(profile)
    await db.commit()  # commit both User + JobSeekerProfile atomically

    return _make_tokens(user)


# =============================================================================
# signup_recruiter
# =============================================================================
# Same as signup_job_seeker but:
#   • Role is RECRUITER
#   • Creates RecruiterProfile with company data from the signup form
# =============================================================================
async def signup_recruiter(
    db: AsyncSession, body: RecruiterSignupSchema
) -> dict:
    """
    Register a new recruiter account with company details.
    Returns tokens on success.  Raises AppError(409) if email exists.
    """
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise AppError("Email already registered", 409)

    user = User(
        name=body.name,
        email=body.email,
        password=hash_password(body.password),
        roles=[Role.RECRUITER],
    )
    db.add(user)
    await db.flush()

    recruiter = RecruiterProfile(
        user_id=user.id,
        company_name=body.company_name,
        company_website=body.company_website,
        description=body.description,
        industry=body.industry,
    )
    db.add(recruiter)
    await db.commit()

    return _make_tokens(user)


# =============================================================================
# upgrade_to_recruiter
# =============================================================================
# A job seeker who wants to also post jobs can "upgrade" their account.
# This:
#   1. Adds "RECRUITER" to their roles array (if not already present).
#   2. Creates a RecruiterProfile for them.
#   3. Issues new tokens that include both roles.
#
# LEARNING CONCEPT ► Idempotency
#   `if Role.RECRUITER not in user.roles` prevents adding the role twice.
#   Calling this function multiple times with the same input has the same result.
# =============================================================================
async def upgrade_to_recruiter(
    db: AsyncSession, user_id: str, body: RecruiterSignupSchema
) -> dict:
    """
    Add recruiter capabilities to an existing job seeker account.
    Returns {"tokens": {...}}.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError("User not found", 404)

    # Check if already a recruiter.
    existing_profile = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
    )
    if existing_profile.scalar_one_or_none():
        raise AppError("User already has a recruiter profile", 409)

    # Add RECRUITER role if not already present.
    if Role.RECRUITER not in user.roles:
        # PostgreSQL ARRAY: we replace the entire array with the updated list.
        user.roles = list(user.roles) + [Role.RECRUITER]

    recruiter_profile = RecruiterProfile(
        user_id=user.id,
        company_name=body.company_name,
        company_website=body.company_website,
        description=body.description,
        industry=body.industry,
    )
    db.add(recruiter_profile)
    await db.commit()
    await db.refresh(user)  # reload from DB to get updated roles

    return {"tokens": _make_tokens(user)}


# =============================================================================
# login
# =============================================================================
# 1. Find user by email (raises 401 if not found — don't reveal which field was wrong).
# 2. Compare submitted password with the stored bcrypt hash.
# 3. Check account is still active.
# 4. Return tokens.
#
# SECURITY NOTE ► "Invalid credentials" for both wrong email AND wrong password.
#   Saying "wrong password" would confirm the email exists (enumeration attack).
#   "Invalid credentials" reveals nothing.
# =============================================================================
async def login(db: AsyncSession, email: str, password: str) -> dict:
    """
    Authenticate and return tokens.
    Raises AppError(401) for invalid credentials or inactive account.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Same error message for "not found" and "wrong password" (security).
    if not user or not compare_passwords(password, user.password):
        raise AppError("Invalid credentials", 401)

    if not user.is_active:
        raise AppError("Account is deactivated", 403)

    return _make_tokens(user)


# =============================================================================
# refresh_tokens
# =============================================================================
# Called by POST /api/auth/refresh when the access token expires.
# 1. Verify the refresh token (raises 401 if expired/invalid).
# 2. Load the user from the database (tokens could be revoked if user is deleted).
# 3. Issue new access + refresh tokens (rotation).
#
# LEARNING CONCEPT ► Token Rotation
#   Each refresh call issues a NEW refresh token.  The old one is implicitly
#   "invalidated" because the client replaces it with the new cookie.
#   (Full revocation would require storing used tokens in Redis.)
# =============================================================================
async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    """
    Validate a refresh token and issue new access + refresh tokens.
    Raises AppError(401) for invalid/expired tokens.
    """
    payload = verify_refresh_token(refresh_token)
    user_id = payload.get("userId")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError("User not found", 401)

    return _make_tokens(user)


# =============================================================================
# get_current_user
# =============================================================================
# Used by GET /api/auth/me to return the current user's info.
# Returns a plain dict (not the SQLAlchemy object) so it can be JSON-serialised.
# =============================================================================
async def get_current_user(db: AsyncSession, user_id: str) -> dict:
    """
    Load a user by ID and return a serialisable dict.
    Raises AppError(404) if the user doesn't exist.

    LEARNING NOTE ► why return a dict instead of the User object?
      SQLAlchemy objects have lazy-loaded relationships and are not directly
      JSON-serialisable.  Converting to a plain dict avoids both issues.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError("User not found", 404)

    return {
        "id":         user.id,
        "name":       user.name,
        "email":      user.email,
        "roles":      [r.value if hasattr(r, "value") else r for r in user.roles],
        "is_active":  user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
