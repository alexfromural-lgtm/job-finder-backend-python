from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.profiles import RecruiterProfile


async def get_recruiter_profile(db: AsyncSession, user_id: str):
    """
    Fetch a recruiter's profile (with user info).
    Mirrors getRecruiterProfile() in recruiter.service.ts.
    """
    result = await db.execute(
        select(RecruiterProfile)
        .options(selectinload(RecruiterProfile.user))
        .where(RecruiterProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_recruiter_profile(db: AsyncSession, user_id: str, data: dict):
    """
    Update recruiter profile fields.
    Mirrors updateRecruiterProfile() in recruiter.service.ts.
    """
    result = await db.execute(
        select(RecruiterProfile)
        .options(selectinload(RecruiterProfile.user))
        .where(RecruiterProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise AppError("Recruiter profile not found", 404)

    for field, value in data.items():
        if value is not None:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


async def get_applications_for_job(
    db: AsyncSession, user_id: str, job_id: str
) -> list[Application]:
    """
    Return all applications for a specific job — verifies recruiter ownership.
    Mirrors getApplicationsForJob() in recruiter.service.ts.
    """
    rec_result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
    )
    recruiter = rec_result.scalar_one_or_none()
    if not recruiter:
        raise AppError("Recruiter profile not found", 404)

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise AppError("Job not found", 404)
    if job.recruiter_id != recruiter.id:
        raise AppError("You are not authorized to view applications for this job", 403)

    result = await db.execute(
        select(Application)
        .options(
            selectinload(Application.job_seeker).selectinload(RecruiterProfile.user)
        )
        .where(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def update_application_status(
    db: AsyncSession,
    user_id: str,
    application_id: str,
    status: ApplicationStatus,
) -> Application:
    """
    Update the status of an application — verifies recruiter ownership.
    Mirrors updateApplicationStatus() in recruiter.service.ts.
    """
    rec_result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
    )
    recruiter = rec_result.scalar_one_or_none()
    if not recruiter:
        raise AppError("Recruiter profile not found", 404)

    app_result = await db.execute(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.id == application_id)
    )
    application = app_result.scalar_one_or_none()

    if not application:
        raise AppError("Application not found", 404)
    if application.job.recruiter_id != recruiter.id:
        raise AppError("You are not authorized to update this application", 403)

    application.status = status
    await db.commit()
    await db.refresh(application)
    return application
