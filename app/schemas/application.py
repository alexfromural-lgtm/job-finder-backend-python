from typing import Optional
from pydantic import BaseModel
from app.models.application import ApplicationStatus


class ApplicationSchema(BaseModel):
    """Mirrors applicationSchema (application.schema.ts)."""

    cover_letter: Optional[str] = None


class ApplicationStatusSchema(BaseModel):
    """Mirrors applicationStatusSchema (application.schema.ts)."""

    status: ApplicationStatus
