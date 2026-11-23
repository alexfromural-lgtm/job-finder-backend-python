# =============================================================================
# app/routers/jobseeker.py  —  JOB SEEKER ENDPOINTS
# =============================================================================
# All routes here require the JOB_SEEKER role.
#
# PROFILE:
#   GET   /api/jobseeker/profile  → get own profile
#   PATCH /api/jobseeker/profile  → update own profile
#
# APPLICATIONS:
#   POST   /api/jobseeker/apply/{job_id}            → apply (queued via Celery)
#   GET    /api/jobseeker/applications              → list own applications
#   DELETE /api/jobseeker/applications/{id}         → withdraw application
#
# SAVED JOBS:
#   POST   /api/jobseeker/saved/{job_id}            → save/bookmark (queued)
#   GET    /api/jobseeker/saved                     → list saved jobs
#   DELETE /api/jobseeker/saved/{job_id}            → unsave a job
#
# LEARNING CONCEPT ► Shared Dependency Variable
#   `_JS_AUTH = Depends(authorize_roles("JOB_SEEKER"))` creates one dependency
#   object that is reused across multiple routes.
#   Benefits: DRY (Don't Repeat Yourself), consistent role enforcement.
#
# LEARNING CONCEPT ► Queued vs Synchronous Operations
#   "Apply" and "save" are queued (return 202 Accepted + task_id).
#   The actual DB write happens asynchronously in a Celery worker.
#   This pattern improves API responsiveness for operations that might be slow
#   or need retry logic (like notifications after applying).
#
#   202 Accepted = "we got your request and are processing it, but it's not done yet"
#   The client polls GET /api/queue/job/{task_id} to check progress.
# =============================================================================

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.queue.tasks import apply_to_job_task, save_job_task
from app.schemas.application import ApplicationSchema
from app.schemas.jobseeker import UpdateJobSeekerProfileSchema
from app.services import jobseeker_service

router = APIRouter()

# Reusable dependency — enforces JOB_SEEKER role on routes that use it.
# `Depends(...)` is called once per request, not once at startup.
_JS_AUTH = Depends(authorize_roles("JOB_SEEKER"))


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================


@router.get("/profile", dependencies=[_JS_AUTH])
async def get_profile(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the authenticated job seeker's profile.
    `auth["userId"]` identifies which profile to load.
    """
    profile = await jobseeker_service.get_job_seeker_profile(db, auth["userId"])
    return {"profile": profile}


@router.patch("/profile", dependencies=[_JS_AUTH])
async def update_profile(
    body: UpdateJobSeekerProfileSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update the job seeker profile.

    LEARNING NOTE ► `body.model_dump(exclude_unset=True)`
      Only sends the fields the client provided to the service.
      If the client sends {"bio": "New bio"}, only bio is updated.
      Other fields (skills, location, etc.) are left unchanged.
    """
    data = body.model_dump(exclude_unset=True)
    profile = await jobseeker_service.update_job_seeker_profile(db, auth["userId"], data)
    return {"profile": profile}


# =============================================================================
# APPLICATION ENDPOINTS
# =============================================================================


@router.post("/apply/{job_id}", status_code=202, dependencies=[_JS_AUTH])
async def apply_to_job(
    job_id: str,
    body: ApplicationSchema,
    auth: Annotated[dict, Depends(require_auth)],
):
    """
    Enqueue an apply-to-job operation.
    Returns 202 + task_id for polling.

    LEARNING CONCEPT ► Celery Task Dispatching
      `apply_to_job_task.delay(user_id, job_id, cover_letter)`:
        • `.delay(...)` sends the task to Redis (the message broker)
        • Returns a `task` object immediately — doesn't wait for completion
        • A Celery worker process picks it up and runs the actual DB insert
        • `task.id` is a UUID the client uses to poll the status

    LEARNING NOTE ► No `db` parameter here!
      The DB work happens in the worker, not in this HTTP handler.
      The handler just enqueues the job and returns immediately.
    """
    task = apply_to_job_task.delay(auth["userId"], job_id, body.cover_letter)
    return {"queueJobId": task.id, "status": "queued"}


@router.get("/applications", dependencies=[_JS_AUTH])
async def get_applications(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """List all applications submitted by this job seeker."""
    applications = await jobseeker_service.get_applications(db, auth["userId"])
    return {"applications": applications}


@router.delete("/applications/{application_id}", dependencies=[_JS_AUTH])
async def withdraw_application(
    application_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Withdraw (delete) an application.
    The service verifies the application belongs to this job seeker.
    """
    await jobseeker_service.withdraw_application(db, auth["userId"], application_id)
    return {"message": "Application withdrawn successfully"}


# =============================================================================
# SAVED JOBS ENDPOINTS
# =============================================================================


@router.post("/saved/{job_id}", status_code=202, dependencies=[_JS_AUTH])
async def save_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
):
    """
    Enqueue a save-job operation.
    Returns 202 + task_id for polling.

    LEARNING NOTE ► same queue pattern as apply_to_job.
      Saving a job is queued because it may need to send a notification or
      do additional processing asynchronously.
    """
    task = save_job_task.delay(auth["userId"], job_id)
    return {"queueJobId": task.id, "status": "queued"}


@router.get("/saved", dependencies=[_JS_AUTH])
async def get_saved_jobs(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """List all jobs bookmarked by this job seeker."""
    saved_jobs = await jobseeker_service.get_saved_jobs(db, auth["userId"])
    return {"savedJobs": saved_jobs}


@router.delete("/saved/{job_id}", dependencies=[_JS_AUTH])
async def unsave_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Remove a job from the saved/bookmarked list."""
    await jobseeker_service.unsave_job(db, auth["userId"], job_id)
    return {"message": "Job removed from saved list"}
