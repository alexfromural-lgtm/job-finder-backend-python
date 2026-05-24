from typing import Optional
from pydantic import BaseModel, field_validator


class JobSchema(BaseModel):
    """Mirrors jobSchema (job.schema.ts)."""

    title: str
    description: str
    requirements: str
    location: str
    salary_range: Optional[str] = None
    category: Optional[str] = None

    @field_validator("title", "description", "requirements", "location")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class JobUpdateSchema(BaseModel):
    """Partial schema for job updates — all fields optional."""

    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
