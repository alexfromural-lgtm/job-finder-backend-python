# =============================================================================
# app/schemas/application.py  —  APPLICATION REQUEST SCHEMAS
# =============================================================================
# Two small schemas:
#   ApplicationSchema       → body when submitting an application (optional cover letter)
#   ApplicationStatusSchema → body when updating application status (recruiter action)
#
# LEARNING CONCEPT ► Reusing Enum Types
#   `ApplicationStatus` is defined in app/models/application.py.
#   We import and reuse it here so the schema and the model stay in sync.
#   If a new status value is added to the enum, the schema automatically
#   accepts it without any changes here.
#
# LEARNING CONCEPT ► Minimal Schemas
#   Not every endpoint needs a large schema.
#   ApplicationSchema is just one optional field — but we still use a schema
#   rather than raw parameters so FastAPI documents it in Swagger (/docs).
# =============================================================================

from typing import Optional
from pydantic import BaseModel
from app.models.application import ApplicationStatus


class ApplicationSchema(BaseModel):
    """
    Mirrors applicationSchema (application.schema.ts).
    Used by POST /api/jobseeker/apply/{job_id}.

    LEARNING EXAMPLE ► the client can omit cover_letter entirely:
        {"cover_letter": "Dear Hiring Manager, ..."}   → with cover letter
        {}                                             → without cover letter
    """
    cover_letter: Optional[str] = None


class ApplicationStatusSchema(BaseModel):
    """
    Mirrors applicationStatusSchema (application.schema.ts).
    Used by PATCH /api/recruiter/applications/{id}/status.

    `status` must be one of: submitted, shortlisted, rejected, under_review.
    Pydantic validates this automatically via the ApplicationStatus enum.

    LEARNING EXAMPLE ► invalid value → 422 error:
        {"status": "approved"}  → 422 Unprocessable Entity
        {"status": "shortlisted"} → valid
    """
    status: ApplicationStatus
