from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.profiles import JobSeekerProfile
from app.models.saved_job import SavedJob


async def get_job_seeker_profile(db: AsyncSession, user_id: str):
    """
    Fetch a job seeker's profile (with user info).
    Mirrors getJobSeekerProfile() in jobseeker.service.ts.
    """
    result = await db.execute(
        select(JobSeekerProfile)
        .options(selectinload(JobSeekerProfile.user))
        .where(JobSeekerProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_job_seeker_profile(db: AsyncSession, user_id: str, data: dict):
    """
    Update job seeker profile fields.
    Mirrors updateJobSeekerProfile() in jobseeker.service.ts.
    """
    result = await db.execute(
        select(JobSeekerProfile)
        .options(selectinload(JobSeekerProfile.user))
        .where(JobSeekerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise AppError("Job seeker profile not found", 404)

    for field, value in data.items():
        if value is not None:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


async def apply_to_job(
    db: AsyncSession, user_id: str, job_id: str, cover_letter: Optional[str] = None
) -> Application:
    """
    Submit a job application.
    Mirrors applyToJob() in jobseeker.service.ts.
    Called both directly and from the Celery worker.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise AppError("Job not found", 404)
    if not job.is_active:
        raise AppError("This job is no longer active", 410)

    existing = await db.execute(
        select(Application).where(
            Application.job_id == job_id,
            Application.job_seeker_id == job_seeker.id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppError("You have already applied to this job", 409)

    application = Application(
        job_id=job_id,
        job_seeker_id=job_seeker.id,
        cover_letter=cover_letter,
        status=ApplicationStatus.submitted,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def get_applications(db: AsyncSession, user_id: str) -> list[Application]:
    """
    Return all applications for a job seeker.
    Mirrors getApplications() in jobseeker.service.ts.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.recruiter))
        .where(Application.job_seeker_id == job_seeker.id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def withdraw_application(
    db: AsyncSession, user_id: str, application_id: str
) -> None:
    """
    Withdraw (delete) a job application.
    Mirrors withdrawApplication() in jobseeker.service.ts.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    app_result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = app_result.scalar_one_or_none()

    if not application:
        raise AppError("Application not found", 404)
    if application.job_seeker_id != job_seeker.id:
        raise AppError("You are not authorized to withdraw this application", 403)

    await db.delete(application)
    await db.commit()


async def save_job(db: AsyncSession, user_id: str, job_id: str) -> SavedJob:
    """
    Save a job (upsert — no-op if already saved).
    Mirrors saveJob() in jobseeker.service.ts.
    Called both directly and from the Celery worker.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    if not job_result.scalar_one_or_none():
        raise AppError("Job not found", 404)

    # Upsert: return existing if already saved
    existing_result = await db.execute(
        select(SavedJob).where(
            SavedJob.job_id == job_id,
            SavedJob.job_seeker_id == job_seeker.id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    saved = SavedJob(job_id=job_id, job_seeker_id=job_seeker.id)
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return saved


async def get_saved_jobs(db: AsyncSession, user_id: str) -> list[SavedJob]:
    """
    Return all saved jobs for a job seeker.
    Mirrors getSavedJobs() in jobseeker.service.ts.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    result = await db.execute(
        select(SavedJob)
        .options(selectinload(SavedJob.job).selectinload(Job.recruiter))
        .where(SavedJob.job_seeker_id == job_seeker.id)
        .order_by(SavedJob.saved_at.desc())
    )
    return list(result.scalars().all())


async def unsave_job(db: AsyncSession, user_id: str, job_id: str) -> None:
    """
    Remove a saved job.
    Mirrors unsaveJob() in jobseeker.service.ts.
    """
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    saved_result = await db.execute(
        select(SavedJob).where(
            SavedJob.job_id == job_id,
            SavedJob.job_seeker_id == job_seeker.id,
        )
    )
    saved = saved_result.scalar_one_or_none()
    if not saved:
        raise AppError("Saved job not found", 404)

    await db.delete(saved)
    await db.commit()
