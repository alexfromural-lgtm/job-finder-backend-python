from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.schemas.job import JobSchema, JobUpdateSchema
from app.services import job_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("/all")
async def get_all_jobs(
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
):
    """Public: return paginated active jobs with optional filters."""
    return await job_service.get_all_jobs(db, category, location, search, page, page_size)


@router.get("/recruiter", dependencies=[Depends(authorize_roles("RECRUITER"))])
async def get_jobs_by_recruiter(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Recruiter: return all jobs posted by this recruiter."""
    # Find recruiter profile id
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    return await job_service.get_jobs_by_recruiter(db, recruiter.id)


# Must be AFTER /recruiter to avoid wildcard catching it
@router.get("/{job_id}")
async def get_job_by_id(job_id: str, db: AsyncSession = Depends(get_db)):
    """Public: return a single job by ID."""
    from app.errors.app_error import AppError
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise AppError("Job not found", 404)
    return job


# ---------------------------------------------------------------------------
# Recruiter-only write endpoints
# ---------------------------------------------------------------------------


@router.post("/", status_code=201, dependencies=[Depends(authorize_roles("RECRUITER"))])
async def create_job(
    body: JobSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Recruiter: create a new job listing."""
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    return await job_service.create_job(db, recruiter.id, body)


@router.put("/{job_id}", dependencies=[Depends(authorize_roles("RECRUITER"))])
async def update_job(
    job_id: str,
    body: JobUpdateSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Recruiter: update an owned job."""
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    return await job_service.update_job(db, job_id, recruiter.id, body)


@router.delete("/{job_id}", status_code=204, dependencies=[Depends(authorize_roles("RECRUITER"))])
async def delete_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Recruiter: delete an owned job."""
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    await job_service.delete_job(db, job_id, recruiter.id)
