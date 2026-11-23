# =============================================================================
# app/services/jobseeker_service.py  —  JOB SEEKER BUSINESS LOGIC
# =============================================================================
# Service functions for job seeker operations:
#   • Profile management (get, update)
#   • Job applications (apply, get, withdraw)
#   • Saved jobs / bookmarks (save, get, unsave)
#
# NOTE: apply_to_job and save_job are called from TWO places:
#   1. The Celery task (in app/queue/tasks.py) — async background execution
#   2. Potentially directly by tests or admin scripts
# This is why the business logic is in a service, not in the router.
#
# LEARNING CONCEPT ► selectinload for Nested Relations
#   Some queries need data from related tables (e.g., the job title for an
#   application, or the recruiter info for a job).
#
#   `selectinload(Application.job).selectinload(Job.recruiter)` loads:
#     1. All applications
#     2. For each application, the associated Job
#     3. For each Job, the associated RecruiterProfile
#   This avoids the N+1 query problem while keeping code readable.
# =============================================================================

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.profiles import JobSeekerProfile
from app.models.saved_job import SavedJob


# =============================================================================
# get_job_seeker_profile
# =============================================================================
# Loads the job seeker's profile including their associated User record.
# `selectinload(JobSeekerProfile.user)` avoids a lazy-load attribute access
# that would trigger an extra query (or fail in async context).
# =============================================================================
async def get_job_seeker_profile(db: AsyncSession, user_id: str):
    """
    Fetch a job seeker's profile (with user info).
    Mirrors getJobSeekerProfile() in jobseeker.service.ts.
    Returns None if no profile found.
    """
    result = await db.execute(
        select(JobSeekerProfile)
        .options(selectinload(JobSeekerProfile.user))
        .where(JobSeekerProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# =============================================================================
# update_job_seeker_profile
# =============================================================================
# `data` is a dict of only the fields to update (from model_dump(exclude_unset=True)).
# We use setattr to dynamically update each provided field.
#
# LEARNING NOTE ► `if value is not None` guard
#   We skip None values so that sending {"bio": null} doesn't erase the bio.
#   Only explicitly provided non-null values are written to the database.
# =============================================================================
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


# =============================================================================
# apply_to_job
# =============================================================================
# Business rules enforced:
#   1. Job seeker must have a profile.
#   2. The job must exist.
#   3. The job must still be active (not deactivated by the recruiter).
#   4. The job seeker can't apply to the same job twice (409 Conflict).
#
# LEARNING CONCEPT ► HTTP 410 Gone vs 404 Not Found
#   404 → the resource never existed (or we don't want to reveal its existence)
#   410 → the resource DID exist but is no longer available
#   We use 410 for deactivated jobs — it's more informative.
# =============================================================================
async def apply_to_job(
    db: AsyncSession, user_id: str, job_id: str, cover_letter: Optional[str] = None
) -> Application:
    """
    Submit a job application.
    Mirrors applyToJob() in jobseeker.service.ts.
    Called both directly and from the Celery worker.
    """
    # Step 1: Verify the job seeker has a profile.
    js_result = await db.execute(
        select(JobSeekerProfile).where(JobSeekerProfile.user_id == user_id)
    )
    job_seeker = js_result.scalar_one_or_none()
    if not job_seeker:
        raise AppError("Job seeker profile not found", 404)

    # Step 2: Verify the job exists.
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise AppError("Job not found", 404)
    if not job.is_active:
        raise AppError("This job is no longer active", 410)  # 410 Gone

    # Step 3: Check for duplicate application.
    existing = await db.execute(
        select(Application).where(
            Application.job_id == job_id,
            Application.job_seeker_id == job_seeker.id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppError("You have already applied to this job", 409)

    # Step 4: Create the application.
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


# =============================================================================
# get_applications
# =============================================================================
# Returns all applications with nested job + recruiter data,
# ordered newest-first (most recent activity at the top).
#
# LEARNING CONCEPT ► Chained selectinload
#   `.selectinload(Application.job).selectinload(Job.recruiter)` chains two
#   levels of eager loading.  SQLAlchemy issues:
#     1. SELECT * FROM applications WHERE job_seeker_id = ?
#     2. SELECT * FROM jobs WHERE id IN (...)
#     3. SELECT * FROM recruiter_profiles WHERE id IN (...)
#   Three queries total, regardless of how many applications exist.
# =============================================================================
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


# =============================================================================
# withdraw_application
# =============================================================================
# Two authorization checks:
#   1. The application must exist.
#   2. The application must belong to THIS job seeker (not someone else's).
#
# LEARNING CONCEPT ► Row-Level Authorization
#   After checking `Depends(authorize_roles("JOB_SEEKER"))` (you ARE a job seeker),
#   we also check `application.job_seeker_id != job_seeker.id` (this is YOUR application).
#   Both checks are necessary — the first is role-level, the second is row-level.
# =============================================================================
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


# =============================================================================
# save_job
# =============================================================================
# "Upsert" behaviour: if the job is already saved, do nothing (no duplicate error).
# This is a defensive no-op pattern for idempotent operations.
#
# LEARNING CONCEPT ► Idempotent POST
#   Normally POST creates a new resource every time.
#   Here, saving a job twice = same as saving once.
#   We handle the duplicate gracefully instead of returning 409.
# =============================================================================
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
    job = job_result.scalar_one_or_none()
    if not job:
        raise AppError("Job not found", 404)

    # Check if already saved — return existing record (upsert / no-op).
    existing = await db.execute(
        select(SavedJob).where(
            SavedJob.job_id == job_id,
            SavedJob.job_seeker_id == job_seeker.id,
        )
    )
    existing_saved = existing.scalar_one_or_none()
    if existing_saved:
        return existing_saved  # already saved, return as-is

    saved_job = SavedJob(
        job_id=job_id,
        job_seeker_id=job_seeker.id,
    )
    db.add(saved_job)
    await db.commit()
    await db.refresh(saved_job)
    return saved_job


# =============================================================================
# get_saved_jobs
# =============================================================================
async def get_saved_jobs(db: AsyncSession, user_id: str) -> list[SavedJob]:
    """
    Return all bookmarked jobs for a job seeker.
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


# =============================================================================
# unsave_job
# =============================================================================
async def unsave_job(db: AsyncSession, user_id: str, job_id: str) -> None:
    """
    Remove a job from the saved list.
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
    saved_job = saved_result.scalar_one_or_none()
    if not saved_job:
        raise AppError("Saved job not found", 404)

    await db.delete(saved_job)
    await db.commit()
