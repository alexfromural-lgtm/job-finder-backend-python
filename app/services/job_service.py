from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.app_error import AppError
from app.models.job import Job
from app.models.profiles import RecruiterProfile
from app.schemas.job import JobSchema, JobUpdateSchema


async def create_job(db: AsyncSession, recruiter_id: str, data: JobSchema) -> Job:
    """
    Create a new job listing.
    Mirrors createJob() in job.service.ts.
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


async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
    """
    Fetch a single job with recruiter info.
    Mirrors getJobById() in job.service.ts.
    """
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.recruiter))
        .where(Job.id == job_id)
    )
    return result.scalar_one_or_none()


async def update_job(
    db: AsyncSession, job_id: str, recruiter_id: str, data: JobUpdateSchema
) -> Job:
    """
    Update a job — verifies recruiter ownership first.
    Mirrors updateJob() in job.service.ts.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise AppError("Job not found", 404)
    if job.recruiter_id != recruiter_id:
        raise AppError("You are not authorized to update this job", 403)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


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


async def get_jobs_by_recruiter(db: AsyncSession, recruiter_id: str) -> list[Job]:
    """
    Return all jobs posted by a specific recruiter.
    Mirrors getJobsByRecruiter() in job.service.ts.
    """
    result = await db.execute(
        select(Job)
        .where(Job.recruiter_id == recruiter_id)
        .order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_jobs(
    db: AsyncSession,
    category: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    Return paginated active jobs with optional filters.
    Mirrors getAllJobs() in job.service.ts (ILIKE for case-insensitive search).
    """
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    skip = (page - 1) * page_size

    query = select(Job).options(selectinload(Job.recruiter)).where(Job.is_active == True)

    if category:
        query = query.where(Job.category == category)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if search:
        query = query.where(
            Job.title.ilike(f"%{search}%")
            | Job.description.ilike(f"%{search}%")
            | Job.requirements.ilike(f"%{search}%")
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    jobs_result = await db.execute(
        query.order_by(Job.created_at.desc()).offset(skip).limit(page_size)
    )
    jobs = list(jobs_result.scalars().all())

    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": -(-total // page_size),  # ceiling division
    }
