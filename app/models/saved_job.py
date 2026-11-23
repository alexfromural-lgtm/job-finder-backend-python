# =============================================================================
# app/models/saved_job.py  —  SAVED JOB (BOOKMARK) MODEL
# =============================================================================
# A SavedJob is a bookmark: a job seeker saving a job listing for later.
#
# LEARNING CONCEPT ► Composite Unique Constraint
#   The UNIQUE constraint on (job_id, job_seeker_id) means:
#     ✓ User A can save Job X once
#     ✗ User A cannot save Job X twice (IntegrityError)
#     ✓ User A can save Job Y (different job)
#     ✓ User B can also save Job X (different user)
#
#   This is a "compound unique key" — uniqueness is enforced across BOTH
#   columns together, not each column individually.
#
# LEARNING CONCEPT ► `__table_args__`
#   This tuple holds extra SQLAlchemy table configuration:
#     • `UniqueConstraint(col1, col2, name=...)` → DB-level unique constraint
#     • `Index(name, col1, col2)` → performance index
#   SQLAlchemy applies these when creating the table (or Alembic generates
#   the corresponding migration SQL).
# =============================================================================

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SavedJob(Base):
    """Mirrors the Prisma SavedJob model."""

    __tablename__ = "saved_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False
    )
    job_seeker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_seeker_profiles.id"), nullable=False
    )

    # ── Timestamp ─────────────────────────────────────────────────────────────
    # `saved_at` records WHEN the job was bookmarked (read-only after creation).
    # Unlike `updated_at`, this never changes — there's no "update a bookmark".
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # Navigate from SavedJob → Job:  saved.job.title
    # Navigate from Job → SavedJobs: job.saved_by (list of bookmarks)
    job: Mapped["Job"] = relationship("Job", back_populates="saved_by")
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="saved_jobs"
    )

    # ── Unique Constraint ─────────────────────────────────────────────────────
    # Prevents a job seeker from saving the same job twice.
    # The `name` parameter is the constraint name in the database — useful for
    # error messages and migrations.
    #
    # LEARNING NOTE ► trailing comma in the tuple:
    #   `__table_args__ = (UniqueConstraint(...),)` — the trailing comma is
    #   required when the tuple has only one element, otherwise Python treats
    #   it as a parenthesised expression, not a tuple.
    __table_args__ = (
        UniqueConstraint("job_id", "job_seeker_id", name="uq_saved_jobs_job_jobseeker"),
    )
