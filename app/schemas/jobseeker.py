from typing import Optional
from pydantic import BaseModel


class UpdateJobSeekerProfileSchema(BaseModel):
    """Mirrors updateJobSeekerProfileSchema (jobseeker.schema.ts)."""

    bio: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[list[str]] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    resume_url: Optional[str] = None
