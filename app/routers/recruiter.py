from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import authorize_roles, require_auth
from app.schemas.application import ApplicationStatusSchema
from app.schemas.recruiter import UpdateRecruiterProfileSchema
from app.services import recruiter_service

router = APIRouter()

_REC_AUTH = Depends(authorize_roles("RECRUITER"))

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/profile", dependencies=[_REC_AUTH])
async def get_profile(
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    profile = await recruiter_service.get_recruiter_profile(db, auth["userId"])
    return {"profile": profile}


@router.patch("/profile", dependencies=[_REC_AUTH])
async def update_profile(
    body: UpdateRecruiterProfileSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    profile = await recruiter_service.update_recruiter_profile(db, auth["userId"], data)
    return {"profile": profile}


# ---------------------------------------------------------------------------
# Applications management
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/applications", dependencies=[_REC_AUTH])
async def get_applications_for_job(
    job_id: str,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    applications = await recruiter_service.get_applications_for_job(db, auth["userId"], job_id)
    return {"applications": applications}


@router.patch("/applications/{application_id}/status", dependencies=[_REC_AUTH])
async def update_application_status(
    application_id: str,
    body: ApplicationStatusSchema,
    auth: Annotated[dict, Depends(require_auth)],
    db: AsyncSession = Depends(get_db),
):
    application = await recruiter_service.update_application_status(
        db, auth["userId"], application_id, body.status
    )
    return {"application": application}
