# =============================================================================
# app/routers/recruiter.py  —  RECRUITER ENDPOINTS
# =============================================================================
# All routes here require the RECRUITER role.
#
# PROFILE:
#   GET   /api/recruiter/profile  → get own company profile
#   PATCH /api/recruiter/profile  → update company profile
#
# APPLICATION MANAGEMENT:
#   GET   /api/recruiter/jobs/{job_id}/applications              → all applicants for a job
#   PATCH /api/recruiter/applications/{application_id}/status    → update applicant status
#
# LEARNING CONCEPT ► Resource Nesting in URLs
#   `/jobs/{job_id}/applications` nests "applications" under "jobs".
#   This clearly expresses that applications belong to a specific job.
#   It's a RESTful design pattern for related resources.
#
#   EXAMPLE:
#   GET /api/recruiter/jobs/abc-123/applications
#   → all applications for job abc-123 (only visible to that job's recruiter)
# =============================================================================

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.schemas.application import ApplicationStatusSchema
from app.schemas.recruiter import UpdateRecruiterProfileSchema
from app.services import recruiter_service

router = APIRouter()

# Reusable dependency — all routes in this router require RECRUITER role.
_REC_AUTH = Depends(authorize_roles("RECRUITER"))


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================


@router.get("/profile", dependencies=[_REC_AUTH])
async def get_profile(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated recruiter's company profile."""
    profile = await recruiter_service.get_recruiter_profile(db, auth["userId"])
    return {"profile": profile}


@router.patch("/profile", dependencies=[_REC_AUTH])
async def update_profile(
    body: UpdateRecruiterProfileSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update the recruiter's company profile.

    LEARNING NOTE ► exclude_unset=True
      Only the fields explicitly sent in the JSON body are updated.
      Sending {"company_name": "ACME"} won't wipe out company_website.
    """
    data = body.model_dump(exclude_unset=True)
    profile = await recruiter_service.update_recruiter_profile(db, auth["userId"], data)
    return {"profile": profile}


# =============================================================================
# APPLICATION MANAGEMENT
# =============================================================================


@router.get("/jobs/{job_id}/applications", dependencies=[_REC_AUTH])
async def get_applications_for_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    List all applications for a specific job posted by this recruiter.

    LEARNING NOTE ► ownership check in the service
      The service verifies the job belongs to this recruiter's profile.
      This prevents one recruiter from viewing another's applicants.
    """
    applications = await recruiter_service.get_applications_for_job(db, auth["userId"], job_id)
    return {"applications": applications}


@router.patch("/applications/{application_id}/status", dependencies=[_REC_AUTH])
async def update_application_status(
    application_id: str,
    body: ApplicationStatusSchema,          # validates status is a valid enum value
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of an application (e.g. shortlist, reject).

    VALID STATUS VALUES: submitted, under_review, shortlisted, rejected
    (enforced by ApplicationStatusSchema → ApplicationStatus enum)

    LEARNING CONCEPT ► Resource Action via PATCH
      PATCH is used for partial updates.
      Here we're updating ONE field (status) of the application resource.
      This is more RESTful than a custom action route like POST /accept.
    """
    application = await recruiter_service.update_application_status(
        db, auth["userId"], application_id, body.status
    )
    return {"application": application}
