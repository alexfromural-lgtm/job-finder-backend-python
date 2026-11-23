# =============================================================================
# app/services/job_service.py  —  JOB LISTING BUSINESS LOGIC
# =============================================================================
# Service functions for creating, reading, updating, and deleting job listings.
#
# LEARNING CONCEPT ► CRUD Operations
#   CRUD = Create, Read, Update, Delete — the four basic data operations.
#   This service implements all four for jobs:
#     CREATE → create_job
#     READ   → get_job_by_id, get_all_jobs, get_jobs_by_recruiter
#     UPDATE → update_job
#     DELETE → delete_job
#
# LEARNING CONCEPT ► SQLAlchemy Async Queries
#   Basic query pattern:
#     result = await db.execute( select(Model).where(condition) )
#     item   = result.scalar_one_or_none()   # None if not found
#     items  = result.scalars().all()         # list of all matches
#
#   `scalar_one_or_none()` → returns ONE item or None (raises if multiple found)
#   `scalar_one()`         → raises if zero or more than one found
#   `.scalars().all()`     → returns all matches as a list
# =============================================================================

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.job import Job
from app.models.profiles import RecruiterProfile
from app.schemas.job import JobSchema, JobUpdateSchema


# =============================================================================
# create_job
# =============================================================================
# 1. Create a Job instance with all required fields.
# 2. `db.add(job)` stages it for INSERT.
# 3. `await db.commit()` executes the INSERT.
# 4. `await db.refresh(job)` reloads the row from the DB (gets created_at, etc.)
#
# LEARNING NOTE ► db.refresh()
#   After commit(), the Python object may be "expired" (attributes are stale).
#   refresh() re-fetches the row from the database so all attributes are current.
#   This is especially important for server-generated values like `created_at`
#   (set by PostgreSQL's NOW() function, not Python code).
# =============================================================================
async def create_job(db: AsyncSession, recruiter_id: str, data: JobSchema) -> Job:
    """
    Create a new job listing.
    Mirrors createJob() in job.service.ts.

    LEARNING EXAMPLE ► the data flow:
      Router receives JSON body → Pydantic validates → JobSchema object
      → create_job(db, recruiter_id, schema_object)
      → new Job ORM object created and committed to DB
    """
    job = Job(
        recruiter_id=recruiter_id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        location=data.location,
        salary_range=data.salary_range,
        category=data.category,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# =============================================================================
# get_job_by_id
# =============================================================================
# `selectinload(Job.recruiter)` eagerly loads the related RecruiterProfile
# in a second SELECT query (not a JOIN).
#
# LEARNING CONCEPT ► Loading Strategies
#   lazy     → loads relationship only when you access the attribute
#               (causes N+1 problem if accessed in a loop)
#   selectin → issues one extra SELECT per relationship type, loading ALL
#               related objects efficiently
#   joined   → adds a JOIN to the main query (good for one-to-one/many-to-one)
#
#   EXAMPLE:
#     selectinload(Job.recruiter)
#     → SELECT * FROM recruiter_profiles WHERE id IN (...)
#     (fetches recruiters for all loaded jobs in one query)
# =============================================================================
async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
    """
    Fetch a single job with recruiter info.
    Mirrors getJobById() in job.service.ts.
    Returns None if the job doesn't exist.
    """
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.recruiter))  # pre-load recruiter data
        .where(Job.id == job_id)
    )
    return result.scalar_one_or_none()


# =============================================================================
# update_job
# =============================================================================
# Two-step update:
#   1. Verify the job exists AND belongs to this recruiter (authorization).
#   2. Apply only the fields that were provided (partial update).
#
# LEARNING CONCEPT ► model_dump(exclude_unset=True)
#   Only the fields explicitly sent in the PATCH body are in `update_data`.
#   `setattr(job, field, value)` dynamically sets `job.title = "new"` etc.
#   After the loop, SQLAlchemy marks the object as "dirty" and the commit
#   generates an UPDATE statement for only the changed columns.
# =============================================================================
async def update_job(
    db: AsyncSession, job_id: str, recruiter_id: str, data: JobUpdateSchema
) -> Job:
    """
    Update a job — verifies recruiter ownership first.
    Mirrors updateJob() in job.service.ts.
    Raises AppError(404) if job not found.
    Raises AppError(403) if the recruiter doesn't own this job.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise AppError("Job not found", 404)
    if job.recruiter_id != recruiter_id:
        raise AppError("You are not authorized to update this job", 403)

    # Apply only the fields that were provided in the request body.
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)  # e.g. setattr(job, "title", "New Title")

    await db.commit()
    await db.refresh(job)
    return job


# =============================================================================
# delete_job
# =============================================================================
# Same ownership check as update_job, then `db.delete(job)` stages a DELETE.
#
# LEARNING NOTE ► `await db.delete(job)` vs raw SQL
#   SQLAlchemy handles cascading deletes based on the relationship configuration.
#   If Job.applications has `cascade="all, delete-orphan"`, deleting a job
#   would automatically delete all its applications.
#   Here, the relationships don't have cascade delete — the router/service
#   should handle related records manually if needed.
# =============================================================================
async def delete_job(db: AsyncSession, job_id: str, recruiter_id: str) -> None:
    """
    Delete a job — verifies recruiter ownership first.
    Mirrors deleteJob() in job.service.ts.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise AppError("Job not found", 404)
    if job.recruiter_id != recruiter_id:
        raise AppError("You are not authorized to delete this job", 403)

    await db.delete(job)
    await db.commit()


# =============================================================================
# get_jobs_by_recruiter
# =============================================================================
# Returns a recruiter's own job listings, most recent first.
# Used by GET /api/jobs/my-jobs (recruiter dashboard).
# =============================================================================
async def get_jobs_by_recruiter(db: AsyncSession, recruiter_id: str) -> list[Job]:
    """
    Return all jobs posted by a specific recruiter.
    Mirrors getJobsByRecruiter() in job.service.ts.
    """
    result = await db.execute(
        select(Job)
        .where(Job.recruiter_id == recruiter_id)
        .order_by(Job.created_at.desc())  # newest first
    )
    return list(result.scalars().all())


# =============================================================================
# get_all_jobs  (paginated + filtered)
# =============================================================================
# More complex query with:
#   • Filtering (category, location, search text)
#   • Pagination (skip/limit)
#   • Count query (for totalPages calculation)
#
# LEARNING CONCEPT ► Pagination with SQLAlchemy
#   `offset(skip).limit(page_size)` is SQL OFFSET/LIMIT:
#     page=1, page_size=10 → offset=0,  limit=10 → rows 1-10
#     page=2, page_size=10 → offset=10, limit=10 → rows 11-20
#
# LEARNING CONCEPT ► ILIKE (case-insensitive LIKE)
#   `.ilike(f"%{search}%")` performs a PostgreSQL case-insensitive search.
#   "python" matches "Python", "PYTHON", "python developer", etc.
#   The `%` wildcard matches any number of characters.
#
# LEARNING CONCEPT ► Ceiling Division
#   `totalPages = -(-total // page_size)` is a Python trick for ceiling division.
#   Normal: 11 // 10 = 1  (misses the second page)
#   Ceiling: -(-11 // 10) = -(- 2) = 2  (correct: 2 pages)
#   Equivalent to: math.ceil(total / page_size)
# =============================================================================
async def get_all_jobs(
    db: AsyncSession,
    category:  Optional[str] = None,
    location:  Optional[str] = None,
    search:    Optional[str] = None,
    page:      int = 1,
    page_size: int = 10,
) -> dict:
    """
    Return paginated active jobs with optional filters.
    Mirrors getAllJobs() in job.service.ts.
    """
    # Clamp page and page_size to sane bounds.
    page      = max(1, page)
    page_size = min(100, max(1, page_size))
    skip      = (page - 1) * page_size

    # Start with the base query: active jobs with recruiter info preloaded.
    query = select(Job).options(selectinload(Job.recruiter)).where(Job.is_active == True)

    # Apply optional filters:
    if category:
        query = query.where(Job.category == category)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))  # case-insensitive
    if search:
        # Search across title, description, AND requirements simultaneously.
        # `|` is SQLAlchemy's OR operator for column expressions.
        query = query.where(
            Job.title.ilike(f"%{search}%")
            | Job.description.ilike(f"%{search}%")
            | Job.requirements.ilike(f"%{search}%")
        )

    # Count total matching records (for pagination metadata).
    # `.subquery()` turns the base query into a subquery, then we count its rows.
    count_query  = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total        = total_result.scalar_one()

    # Fetch the actual page of jobs.
    jobs_result = await db.execute(
        query.order_by(Job.created_at.desc()).offset(skip).limit(page_size)
    )
    jobs = list(jobs_result.scalars().all())

    return {
        "jobs":        jobs,
        "total":       total,
        "page":        page,
        "pageSize":    page_size,
        "totalPages":  -(-total // page_size),  # ceiling division
    }
