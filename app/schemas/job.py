# =============================================================================
# app/schemas/job.py  —  JOB REQUEST VALIDATION SCHEMAS
# =============================================================================
# Two schemas cover the job CRUD operations:
#   JobSchema       → creating a new job (all required fields must be present)
#   JobUpdateSchema → updating an existing job (all fields optional / PATCH)
#
# LEARNING CONCEPT ► Creating vs Updating (POST vs PATCH)
#   POST   → creates a resource; all required fields must be provided.
#   PATCH  → partial update; only send fields you want to change.
#
#   For PATCH we make all fields Optional with a default of None.
#   In the service, we call `model_dump(exclude_unset=True)` to get only
#   the fields the client actually provided (not the None defaults).
#
#   EXAMPLE:
#     PATCH body:  {"title": "New Title"}
#     model_dump(exclude_unset=True) → {"title": "New Title"}  (only 1 key)
#     model_dump()                   → {"title": "New Title", "description": None, ...}
#
# LEARNING CONCEPT ► Validating Multiple Fields at Once
#   `@field_validator("field1", "field2", "field3")` applies ONE validator
#   function to multiple fields.  FastAPI/Pydantic calls it once per field.
# =============================================================================

from typing import Optional
from pydantic import BaseModel, field_validator


class JobSchema(BaseModel):
    """Mirrors jobSchema (job.schema.ts). Used for job creation (POST)."""

    title:        str           # required — a job must have a title
    description:  str           # required
    requirements: str           # required
    location:     str           # required
    salary_range: Optional[str] = None  # optional — not all jobs list salary
    category:     Optional[str] = None  # optional — e.g. "Engineering", "Product"

    # Validates all four required string fields are not just whitespace.
    # `@field_validator("a", "b")` → runs for "a" then again for "b".
    @field_validator("title", "description", "requirements", "location")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class JobUpdateSchema(BaseModel):
    """
    Partial schema for job updates — all fields optional.
    Used for PATCH /api/jobs/{id}.

    LEARNING EXAMPLE:
        body = JobUpdateSchema(**{"title": "Updated Title"})
        data = body.model_dump(exclude_unset=True)
        # data = {"title": "Updated Title"}  — only the field we sent

        for field, value in data.items():
            setattr(job, field, value)   # update only provided fields
    """

    title:        Optional[str]  = None
    description:  Optional[str]  = None
    requirements: Optional[str]  = None
    location:     Optional[str]  = None
    salary_range: Optional[str]  = None
    category:     Optional[str]  = None
    is_active:    Optional[bool] = None  # recruiters can deactivate/reactivate jobs
