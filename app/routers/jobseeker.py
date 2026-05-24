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

_JS_AUTH = Depends(authorize_roles("JOB_SEEKER"))

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/profile", dependencies=[_JS_AUTH])
async def get_profile(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    profile = await jobseeker_service.get_job_seeker_profile(db, auth["userId"])
    return {"profile": profile}


@router.patch("/profile", dependencies=[_JS_AUTH])
async def update_profile(
    body: UpdateJobSeekerProfileSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    profile = await jobseeker_service.update_job_seeker_profile(db, auth["userId"], data)
    return {"profile": profile}


# ---------------------------------------------------------------------------
# Applications — apply is queued; withdraw is synchronous
# ---------------------------------------------------------------------------


@router.post("/apply/{job_id}", status_code=202, dependencies=[_JS_AUTH])
async def apply_to_job(
    job_id: str,
    body: ApplicationSchema,
    auth: Annotated[dict, Depends(require_auth)],
):
    """
    Enqueue an apply-to-job operation.
    Returns 202 + task_id for polling, identical to the Bull pattern.
    Mirrors the jobseeker router in jobseeker.route.ts.
    """
    task = apply_to_job_task.delay(auth["userId"], job_id, body.cover_letter)
    return {"queueJobId": task.id, "status": "queued"}


@router.get("/applications", dependencies=[_JS_AUTH])
async def get_applications(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    applications = await jobseeker_service.get_applications(db, auth["userId"])
    return {"applications": applications}


@router.delete("/applications/{application_id}", dependencies=[_JS_AUTH])
async def withdraw_application(
    application_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    await jobseeker_service.withdraw_application(db, auth["userId"], application_id)
    return {"message": "Application withdrawn successfully"}


# ---------------------------------------------------------------------------
# Saved jobs — save is queued; get/delete are synchronous
# ---------------------------------------------------------------------------


@router.post("/saved/{job_id}", status_code=202, dependencies=[_JS_AUTH])
async def save_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
):
    """
    Enqueue a save-job operation.
    Returns 202 + task_id for polling.
    """
    task = save_job_task.delay(auth["userId"], job_id)
    return {"queueJobId": task.id, "status": "queued"}


@router.get("/saved", dependencies=[_JS_AUTH])
async def get_saved_jobs(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    saved_jobs = await jobseeker_service.get_saved_jobs(db, auth["userId"])
    return {"savedJobs": saved_jobs}


@router.delete("/saved/{job_id}", dependencies=[_JS_AUTH])
async def unsave_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    await jobseeker_service.unsave_job(db, auth["userId"], job_id)
    return {"message": "Job removed from saved list"}
