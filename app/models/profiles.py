# =============================================================================
# app/models/profiles.py  —  JOB SEEKER & RECRUITER PROFILE MODELS
# =============================================================================
# Both profile types extend the core User with role-specific data.
# They are separate tables rather than columns on the users table because:
#   • A user might have BOTH roles (upgraded from job seeker to recruiter)
#   • Each role's data is very different — mixing them in one table wastes space
#
# LEARNING CONCEPT ► One-to-One Relationship
#   Each User has at most one JobSeekerProfile and at most one RecruiterProfile.
#   The profiles table stores `user_id` (foreign key) with a UNIQUE constraint,
#   which enforces the one-to-one relationship at the database level.
#
#   EXAMPLE: user_id column in job_seeker_profiles has UNIQUE constraint:
#     ✓ user_id = "abc" appears once  → valid
#     ✗ user_id = "abc" appears twice → IntegrityError (duplicate)
#
# LEARNING CONCEPT ► PostgreSQL ARRAY column
#   `skills: ARRAY(String)` stores a list of strings in a single column.
#   Alternative would be a separate `skills` table (normalized), but
#   ARRAY is simpler for this use case.
#
#   EXAMPLE in Python:
#     profile.skills = ["Python", "FastAPI", "SQL"]
#   EXAMPLE in PostgreSQL:
#     SELECT * FROM job_seeker_profiles WHERE 'Python' = ANY(skills);
# =============================================================================

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# =============================================================================
# JOB SEEKER PROFILE
# =============================================================================
class JobSeekerProfile(Base):
    """Mirrors the Prisma JobSeekerProfile model."""

    __tablename__ = "job_seeker_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # `unique=True` enforces one profile per user at the DB level.
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False
    )

    # ── Optional Profile Fields ───────────────────────────────────────────────
    # All fields below are nullable — the job seeker fills them in gradually.
    bio:        Mapped[str | None] = mapped_column(String, nullable=True)
    location:   Mapped[str | None] = mapped_column(String, nullable=True)
    # ARRAY(String) → PostgreSQL TEXT[] — stores ["Python", "React", ...].
    # `default=list` → new profiles start with an empty skills list.
    skills:     Mapped[list[str]]  = mapped_column(ARRAY(String), nullable=False, default=list)
    education:  Mapped[str | None] = mapped_column(String, nullable=True)
    experience: Mapped[str | None] = mapped_column(String, nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="job_seeker")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job_seeker", lazy="select"
    )
    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="job_seeker", lazy="select"
    )


# =============================================================================
# RECRUITER PROFILE
# =============================================================================
class RecruiterProfile(Base):
    """Mirrors the Prisma RecruiterProfile model."""

    __tablename__ = "recruiter_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False
    )

    # ── Company Information ───────────────────────────────────────────────────
    company_name:    Mapped[str]       = mapped_column(String, nullable=False)
    company_website: Mapped[str | None] = mapped_column(String, nullable=True)
    description:     Mapped[str | None] = mapped_column(String, nullable=True)
    industry:        Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="recruiter")
    # A recruiter can post many jobs — one-to-many relationship.
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="recruiter", lazy="select"
    )
