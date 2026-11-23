# =============================================================================
# app/services/recruiter_service.py  —  RECRUITER BUSINESS LOGIC
# =============================================================================
# Service functions for recruiter operations:
#   • Profile management (get, update)
#   • Application management (view applicants, update status)
#
# LEARNING CONCEPT ► Ownership Chain
#   Before a recruiter can view or change an application, we verify:
#     1. The recruiter has a profile.
#     2. The job belongs to that recruiter's profile.
#     3. The application belongs to that job.
#   This "ownership chain" prevents one recruiter from accessing another's data.
# =============================================================================

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.profiles import RecruiterProfile


# =============================================================================
# get_recruiter_profile
# =============================================================================
async def get_recruiter_profile(db: AsyncSession, user_id: str):
    """
    Fetch the recruiter's profile including user info.
    Mirrors getRecruiterProfile() in recruiter.service.ts.
    """
    result = await db.execute(
        select(RecruiterProfile)
        .options(selectinload(RecruiterProfile.user))
        .where(RecruiterProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# =============================================================================
# update_recruiter_profile
# =============================================================================
async def update_recruiter_profile(db: AsyncSession, user_id: str, data: dict):
    """
    Update recruiter company profile fields.
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


# =============================================================================
# get_applications_for_job
# =============================================================================
# Two authorization steps:
#   1. Load the recruiter's profile → get recruiter.id
#   2. Load the job → verify job.recruiter_id == recruiter.id
#   3. Load all applications for that job, with job seeker user info preloaded
#
# LEARNING CONCEPT ► Ownership verification via FK comparison
#   `if job.recruiter_id != recruiter.id` is a simple, fast ownership check.
#   It compares two string UUIDs — no extra DB query needed.
# =============================================================================
async def get_applications_for_job(
    db: AsyncSession, user_id: str, job_id: str
) -> list[Application]:
    """
    Return all applications for a job, with job seeker profiles.
    Recruiter ownership is verified before returning data.
    Mirrors getApplicationsForJob() in recruiter.service.ts.
    """
    # Verify recruiter profile exists.
    rec_result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
    )
    recruiter = rec_result.scalar_one_or_none()
    if not recruiter:
        raise AppError("Recruiter profile not found", 404)

    # Verify this job belongs to this recruiter.
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise AppError("Job not found", 404)
    if job.recruiter_id != recruiter.id:
        raise AppError("You are not authorized to view applications for this job", 403)

    # Load applications with job seeker + user data.
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_seeker).selectinload(RecruiterProfile.user))
        .where(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


# =============================================================================
# update_application_status
# =============================================================================
# Recruiter action: move an application through its lifecycle.
#
# Authorization chain:
#   recruiter → job → application
#   "This application belongs to a job I own."
#
# LEARNING CONCEPT ► State Machine
#   The application status follows a state machine:
#     submitted → under_review → shortlisted → rejected (or any direction)
#   The enum constrains which values are valid; business rules (not here)
#   could constrain which transitions are allowed.
# =============================================================================
async def update_application_status(
    db: AsyncSession,
    user_id: str,
    application_id: str,
    status: ApplicationStatus,
) -> Application:
    """
    Update the status of an application.
    Verifies the recruiter owns the associated job.
    Mirrors updateApplicationStatus() in recruiter.service.ts.

    LEARNING EXAMPLE ► state transition:
      application.status = "submitted"
      PATCH body: {"status": "shortlisted"}
      → application.status = "shortlisted"
      → recruiter can now schedule an interview
    """
    # Verify recruiter profile.
    rec_result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
    )
    recruiter = rec_result.scalar_one_or_none()
    if not recruiter:
        raise AppError("Recruiter profile not found", 404)

    # Load application with related job.
    app_result = await db.execute(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.id == application_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise AppError("Application not found", 404)

    # Verify the application's job belongs to this recruiter.
    if application.job.recruiter_id != recruiter.id:
        raise AppError("You are not authorized to update this application", 403)

    # Apply the new status.
    application.status = status
    await db.commit()
    await db.refresh(application)
    return application
