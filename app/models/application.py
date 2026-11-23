# =============================================================================
# app/models/application.py  —  JOB APPLICATION DATABASE MODEL
# =============================================================================
# A job application links a JobSeekerProfile to a Job.
# It tracks the application lifecycle via the `status` column.
#
# LEARNING CONCEPT ► Many-to-Many via Junction Table
#   A job seeker can apply to many jobs.
#   A job can receive many applications.
#   This many-to-many relationship is resolved by the `applications` table
#   (a junction / join table) with extra data (cover_letter, status, timestamps).
#
# LEARNING CONCEPT ► Enum Column in the Database
#   Rather than storing arbitrary strings in the status column,
#   we store one of four fixed values.  The database enforces this:
#   if you try to insert "approved" (not in the enum), it fails.
#
#   SQLAlchemy Enum + Python enum.Enum:
#     1. Python enum defines allowed values in code.
#     2. `Enum(ApplicationStatus, name="applicationstatus")` creates a
#        CORRESPONDING enum type IN PostgreSQL with the same values.
# =============================================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# =============================================================================
# APPLICATION STATUS ENUM
# =============================================================================
# The four lifecycle stages of an application:
#   submitted   → job seeker just applied
#   under_review → recruiter is reviewing it
#   shortlisted  → recruiter is interested
#   rejected     → recruiter declined
#
# LEARNING EXAMPLE ► using in service code:
#   application.status = ApplicationStatus.shortlisted
#   if application.status == ApplicationStatus.rejected:
#       # send rejection email
# =============================================================================
class ApplicationStatus(str, enum.Enum):
    submitted    = "submitted"
    shortlisted  = "shortlisted"
    rejected     = "rejected"
    under_review = "under_review"


# =============================================================================
# APPLICATION MODEL
# =============================================================================
class Application(Base):
    """Mirrors the Prisma Application model."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    # Both foreign keys are non-nullable — an application MUST have both a
    # job and a job seeker.
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False
    )
    job_seeker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_seeker_profiles.id"), nullable=False
    )

    # ── Optional Cover Letter ─────────────────────────────────────────────────
    # `nullable=True` → the job seeker can submit without a cover letter.
    cover_letter: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Status Enum Column ────────────────────────────────────────────────────
    # `Enum(ApplicationStatus, name="applicationstatus")` creates a PostgreSQL
    # native ENUM type called "applicationstatus" in the database.
    # `default=ApplicationStatus.submitted` → new applications start as submitted.
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
        default=ApplicationStatus.submitted,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # Navigate from Application → Job:  application.job.title
    # Navigate from Job → Applications:  job.applications (list)
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="applications"
    )
