from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class RecruiterSignupSchema(BaseModel):
    """Mirrors recruiterSignupSchema (recruiter.schema.ts)."""

    name: str
    email: EmailStr
    password: str
    company_name: str
    company_website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None

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

    company_name: Optional[str] = None
    company_website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
