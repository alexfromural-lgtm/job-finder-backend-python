# =============================================================================
# app/schemas/recruiter.py  —  RECRUITER SIGNUP & PROFILE SCHEMAS
# =============================================================================
# Two schemas:
#   RecruiterSignupSchema        → POST /api/auth/signup/recruiter
#                                   and POST /api/auth/upgrade/recruiter
#   UpdateRecruiterProfileSchema → PATCH /api/recruiter/profile
#
# LEARNING NOTE ► RecruiterSignupSchema extends the SignupSchema concept
#   It includes user credentials (name, email, password) PLUS company info.
#   This avoids a two-step registration flow where the user first creates
#   an account and then fills in company details separately.
# =============================================================================

from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class RecruiterSignupSchema(BaseModel):
    """Mirrors recruiterSignupSchema (recruiter.schema.ts)."""

    # ── User credentials ──────────────────────────────────────────────────────
    name:     str
    email:    EmailStr
    password: str

    # ── Company details ───────────────────────────────────────────────────────
    company_name:    str           # required — must have a company
    company_website: Optional[str] = None  # e.g. "https://acme.com"
    description:     Optional[str] = None  # company description
    industry:        Optional[str] = None  # e.g. "Technology", "Healthcare"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("company_name")
    @classmethod
    def company_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Company name is required")
        return v


class UpdateRecruiterProfileSchema(BaseModel):
    """Mirrors updateRecruiterProfileSchema (recruiter-profile.schema.ts)."""

    # All fields optional for PATCH — update only what you send.
    company_name:    Optional[str] = None
    company_website: Optional[str] = None
    description:     Optional[str] = None
    industry:        Optional[str] = None
