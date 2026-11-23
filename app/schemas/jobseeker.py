# =============================================================================
# app/schemas/jobseeker.py  —  JOB SEEKER PROFILE UPDATE SCHEMA
# =============================================================================
# Used by PATCH /api/jobseeker/profile.
# All fields are optional so the job seeker can update only what they want.
#
# LEARNING CONCEPT ► `Optional[list[str]]`
#   `Optional[X]` is shorthand for `Union[X, None]` — the value can be X or None.
#   `Optional[list[str]]` means: either a list of strings, or None.
#
#   EXAMPLE JSON bodies:
#     {"skills": ["Python", "React"]}    → updates only skills
#     {"bio": "I love coding"}           → updates only bio
#     {"skills": ["Go"], "location": "NYC"} → updates two fields
# =============================================================================

from typing import Optional
from pydantic import BaseModel


class UpdateJobSeekerProfileSchema(BaseModel):
    """Mirrors updateJobSeekerProfileSchema (jobseeker.schema.ts)."""

    bio:        Optional[str]       = None
    location:   Optional[str]       = None
    skills:     Optional[list[str]] = None  # e.g. ["Python", "FastAPI", "SQL"]
    education:  Optional[str]       = None
    experience: Optional[str]       = None
    resume_url: Optional[str]       = None  # URL to uploaded CV/resume file
