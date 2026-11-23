# =============================================================================
# app/routers/jobs.py  —  JOB LISTING ENDPOINTS
# =============================================================================
# Public and protected endpoints for browsing and managing job listings.
#
# PUBLIC (no auth required):
#   GET /api/jobs/all        → paginated + filtered list of active jobs
#   GET /api/jobs/{id}       → single job detail
#
# PROTECTED (recruiter only):
#   POST   /api/jobs/        → create a new job
#   PUT    /api/jobs/{id}    → update an existing job
#   DELETE /api/jobs/{id}    → delete a job
#   GET    /api/jobs/my-jobs → recruiter's own job listings
#
# LEARNING CONCEPT ► Query Parameters
#   Query parameters appear after `?` in the URL:
#   GET /api/jobs/all?category=Engineering&location=NYC&page=2
#
#   In FastAPI, declare them as function arguments with `Query(...)`:
#     category: Optional[str] = Query(default=None)
#   FastAPI reads them from the URL automatically.
#
# LEARNING CONCEPT ► Mixed Public + Protected Routes in One Router
#   Some endpoints here are public (no Depends on auth).
#   Others use `dependencies=[Depends(authorize_roles("RECRUITER"))]` to
#   restrict access.  FastAPI evaluates dependencies before the handler runs.
# =============================================================================

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.schemas.job import JobSchema, JobUpdateSchema
from app.services import job_service

router = APIRouter()


# =============================================================================
# PUBLIC ENDPOINTS — no authentication required
# =============================================================================


@router.get("/all")
async def get_all_jobs(
    db: AsyncSession = Depends(get_db),
    # Optional query parameters with defaults:
    category: Optional[str] = Query(default=None),   # ?category=Engineering
    location: Optional[str] = Query(default=None),   # ?location=NYC
    search:   Optional[str] = Query(default=None),   # ?search=python
    page:     int           = Query(default=1),       # ?page=2
    page_size: int          = Query(default=10),      # ?pageSize=20
):
    """
    Return paginated active jobs with optional filters.

    LEARNING EXAMPLE ► full URL with all query params:
      GET /api/jobs/all?category=Engineering&location=Remote&search=python&page=1&pageSize=10

    LEARNING CONCEPT ► Pagination
      Instead of returning ALL jobs (could be thousands), we return a "page".
      `page=1, page_size=10` → rows 1-10
      `page=2, page_size=10` → rows 11-20
      The service returns `total` so the client knows how many pages exist.
    """
    result = await job_service.get_all_jobs(
        db,
        category=category,
        location=location,
        search=search,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/my-jobs", dependencies=[Depends(authorize_roles("RECRUITER"))])
async def get_my_jobs(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Return all jobs posted by the authenticated recruiter.

    LEARNING NOTE ► two Depends on `auth`:
      `dependencies=[Depends(authorize_roles("RECRUITER"))]` → ensures the role
      `auth: Annotated[dict, Depends(require_auth)]` → injects the JWT payload
      Both run, but only `require_auth` returns a value we capture in `auth`.
    """
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    jobs = await job_service.get_jobs_by_recruiter(db, recruiter.id)
    return {"jobs": jobs}


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch a single job by its UUID.
    Public — anyone can view job details.

    LEARNING CONCEPT ► Path Parameters
      `{job_id}` in the route pattern becomes a function argument:
        GET /api/jobs/abc-123  → job_id = "abc-123"
    """
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        from app.errors.app_error import AppError
        raise AppError("Job not found", 404)
    return {"job": job}


# =============================================================================
# PROTECTED ENDPOINTS — recruiter only
# =============================================================================


@router.post("/", status_code=201, dependencies=[Depends(authorize_roles("RECRUITER"))])
async def create_job(
    body: JobSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new job listing.
    The recruiter's profile is looked up from their user ID.

    LEARNING FLOW:
      JWT → auth["userId"] → RecruiterProfile → new Job linked to that profile
    """
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    job = await job_service.create_job(db, recruiter.id, body)
    return {"message": "Job created successfully!", "job": job}


@router.put("/{job_id}", dependencies=[Depends(authorize_roles("RECRUITER"))])
async def update_job(
    job_id: str,
    body: JobUpdateSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update a job listing.
    The service verifies the recruiter owns this job before updating.
    """
    from sqlalchemy import select
    from app.models.profiles import RecruiterProfile
    result = await db.execute(
        select(RecruiterProfile).where(RecruiterProfile.user_id == auth["userId"])
    )
    recruiter = result.scalar_one_or_none()
    if not recruiter:
        from app.errors.app_error import AppError
        raise AppError("Recruiter profile not found", 404)
    job = await job_service.update_job(db, job_id, recruiter.id, body)
    return {"message": "Job updated successfully!", "job": job}


@router.delete("/{job_id}", dependencies=[Depends(authorize_roles("RECRUITER"))])
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
    return {"message": "Job deleted successfully!"}
