from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.user import User, Role
from app.models.profiles import JobSeekerProfile, RecruiterProfile
from app.schemas.recruiter import RecruiterSignupSchema
from app.utils.hash import hash_password, compare_passwords
from app.utils.auth_utils import check_user_exists_by_email, generate_tokens_for_user
from app.utils.token import verify_refresh_token


async def signup_job_seeker(
    db: AsyncSession, name: str, email: str, password: str
) -> dict:
    """
    Register a new job seeker account.
    Mirrors signupJobSeeker() in auth.service.ts.
    """
    await check_user_exists_by_email(db, email)

    hashed = hash_password(password)
    user = User(
        name=name,
        email=email,
        password=hashed,
        roles=[Role.JOB_SEEKER],
    )
    db.add(user)
    await db.flush()  # get user.id before committing

    profile = JobSeekerProfile(user_id=user.id, skills=[])
    db.add(profile)
    await db.commit()

    return generate_tokens_for_user(user.id, user.roles)


async def signup_recruiter(db: AsyncSession, data: RecruiterSignupSchema) -> dict:
    """
    Register a new recruiter account.
    Mirrors signupRecruiter() in auth.service.ts.
    """
    await check_user_exists_by_email(db, data.email)

    hashed = hash_password(data.password)
    user = User(
        name=data.name,
        email=data.email,
        password=hashed,
        roles=[Role.RECRUITER],
    )
    db.add(user)
    await db.flush()

    profile = RecruiterProfile(
        user_id=user.id,
        company_name=data.company_name,
        company_website=data.company_website,
        description=data.description,
        industry=data.industry,
    )
    db.add(profile)
    await db.commit()

    return generate_tokens_for_user(user.id, user.roles)


async def upgrade_to_recruiter(
    db: AsyncSession, user_id: str, data: RecruiterSignupSchema
) -> dict:
    """
    Upgrade an existing JOB_SEEKER to also hold the RECRUITER role.
    Mirrors upgradeToRecruiter() in auth.service.ts.
    """
    result = await db.execute(
        select(User).options(selectinload(User.recruiter)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise AppError("User not found", 404)
    if Role.JOB_SEEKER not in user.roles:
        raise AppError("Only Job Seekers can upgrade to Recruiter", 403)
    if user.recruiter:
        raise AppError("User already has a recruiter profile", 409)

    user.roles = list(user.roles) + [Role.RECRUITER]
    profile = RecruiterProfile(
        user_id=user.id,
        company_name=data.company_name,
        company_website=data.company_website,
        description=data.description,
        industry=data.industry,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    tokens = generate_tokens_for_user(user.id, user.roles)
    return {"user": user, "tokens": tokens}


async def login(db: AsyncSession, email: str, password: str) -> dict:
    """
    Validate credentials and return JWT tokens.
    Mirrors login() in auth.service.ts.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise AppError("Invalid email or password", 401)
    if not user.is_active:
        raise AppError("Account is deactivated", 403)
    if not compare_passwords(password, user.password):
        raise AppError("Invalid email or password", 401)  # same msg — avoids leaking which field is wrong

    return generate_tokens_for_user(user.id, user.roles)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    """
    Verify a refresh token and issue a new pair.
    Mirrors refreshTokens() in auth.service.ts.
    """
    payload = verify_refresh_token(refresh_token)

    result = await db.execute(select(User).where(User.id == payload["userId"]))
    user = result.scalar_one_or_none()

    if not user:
        raise AppError("User not found", 404)
    if not user.is_active:
        raise AppError("Account is deactivated", 403)

    return generate_tokens_for_user(user.id, user.roles)


async def get_current_user(db: AsyncSession, user_id: str) -> dict:
    """
    Return the current authenticated user's public data.
    Mirrors getCurrentUser() in auth.service.ts.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AppError("User not found", 404)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "roles": user.roles,
        "isActive": user.is_active,
        "createdAt": user.created_at.isoformat(),
        "updatedAt": user.updated_at.isoformat(),
    }
