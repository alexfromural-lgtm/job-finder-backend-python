# =============================================================================
# app/models/job.py  —  JOB LISTING DATABASE MODEL
# =============================================================================
# Maps the `jobs` table.  A Job belongs to a Recruiter and can have:
#   • many Applications (job seekers applying)
#   • many SavedJobs    (job seekers bookmarking it)
#   • many Reports      (users reporting inappropriate content)
#
# LEARNING CONCEPT ► Foreign Keys
#   A foreign key is a column that holds the primary key of a row in ANOTHER
#   table.  This enforces referential integrity — you cannot have a Job that
#   refers to a non-existent RecruiterProfile.
#
#   EXAMPLE:
#     jobs.recruiter_id  →  recruiter_profiles.id
#     If you try to insert a Job with an invalid recruiter_id, the database
#     raises an IntegrityError (caught by the error handler in main.py).
#
# LEARNING CONCEPT ► Database Indexes
#   An index is a data structure that makes certain queries MUCH faster.
#   Without an index, every query scans ALL rows.
#   With an index, the DB jumps directly to matching rows.
#
#   RULE OF THUMB: add indexes on columns you filter by frequently.
#   This project adds composite indexes for common filter patterns:
#     - is_active + category  (browsing jobs by category)
#     - is_active + created_at (listing recent active jobs)
# =============================================================================

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    """Mirrors the Prisma Job model."""

    __tablename__ = "jobs"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign Key: recruiter ────────────────────────────────────────────────
    # `ForeignKey("recruiter_profiles.id")` references the `id` column of the
    # `recruiter_profiles` table.  The database enforces this relationship.
    # Deleting a RecruiterProfile while Jobs reference it would fail unless
    # `ON DELETE CASCADE` or `ON DELETE SET NULL` is configured.
    recruiter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("recruiter_profiles.id"), nullable=False
    )

    # ── Job Details ───────────────────────────────────────────────────────────
    title:        Mapped[str]       = mapped_column(String, nullable=False)
    description:  Mapped[str]       = mapped_column(String, nullable=False)
    requirements: Mapped[str]       = mapped_column(String, nullable=False)
    location:     Mapped[str]       = mapped_column(String, nullable=False)
    # `str | None` = Optional[str] — this column can be NULL in the database.
    salary_range: Mapped[str | None] = mapped_column(String, nullable=True)
    category:     Mapped[str | None] = mapped_column(String, nullable=True)
    is_active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)

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
    # `back_populates="jobs"` means RecruiterProfile.jobs ↔ Job.recruiter
    recruiter: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile", back_populates="jobs"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job", lazy="select"
    )
    saved_by: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="job", lazy="select"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="reported_job", lazy="select"
    )

    # ── Database Indexes ──────────────────────────────────────────────────────
    # `__table_args__` is a tuple of extra table configuration.
    # Each `Index(name, col1, col2, ...)` creates a composite index.
    #
    # LEARNING EXAMPLE ► which query each index speeds up:
    #   ix_jobs_is_active          → SELECT * FROM jobs WHERE is_active = TRUE
    #   ix_jobs_is_active_category → WHERE is_active=TRUE AND category='Engineering'
    #   ix_jobs_recruiter_created  → WHERE recruiter_id=? ORDER BY created_at DESC
    #   ix_jobs_is_active_created  → WHERE is_active=TRUE ORDER BY created_at DESC
    __table_args__ = (
        Index("ix_jobs_is_active",          "is_active"),
        Index("ix_jobs_is_active_category", "is_active", "category"),
        Index("ix_jobs_recruiter_created",  "recruiter_id", "created_at"),
        Index("ix_jobs_is_active_created",  "is_active",    "created_at"),
    )
