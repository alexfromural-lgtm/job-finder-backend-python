# =============================================================================
# app/models/report.py  —  REPORT / MODERATION MODEL
# =============================================================================
# Users can report inappropriate content — either a job posting or another user.
# Reports are reviewed by admins.
#
# LEARNING CONCEPT ► Nullable Foreign Keys (Polymorphic-style)
#   This model has TWO optional foreign keys — a report targets EITHER a job
#   OR a user (or potentially both).  The nullable FK approach means:
#   • `reported_user_id` is NULL if the report is about a job
#   • `reported_job_id` is NULL if the report is about a user
#
#   An alternative would be a polymorphic "content_type" + "content_id" pattern,
#   but explicit nullable FKs are simpler and more DB-native.
#
# LEARNING CONCEPT ► Multiple Relationships to the Same Table
#   Report has TWO foreign keys that both point to the `users` table:
#   • reporter_id        → the user who filed the report
#   • reported_user_id   → the user being reported (nullable)
#
#   SQLAlchemy needs `foreign_keys=[...]` to disambiguate which FK each
#   relationship uses.  Without it, SQLAlchemy can't tell which FK to JOIN on.
#
#   EXAMPLE in service code:
#     report.reporter        → User who filed the report
#     report.reported_user   → User who was reported (may be None)
#     report.reported_job    → Job that was reported (may be None)
# =============================================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# =============================================================================
# REPORT STATUS ENUM
# =============================================================================
# Admin workflow:
#   open      → new, awaiting admin review
#   reviewed  → admin looked at it and took action
#   dismissed → admin determined no action needed
# =============================================================================
class ReportStatus(str, enum.Enum):
    open      = "open"
    reviewed  = "reviewed"
    dismissed = "dismissed"


class Report(Base):
    """Mirrors the Prisma Report model."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── The User Who Reported ─────────────────────────────────────────────────
    reporter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    # ── What Was Reported (one or both may be set) ────────────────────────────
    # `nullable=True` → these are optional foreign keys
    reported_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    reported_job_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=True
    )

    # ── Report Content ────────────────────────────────────────────────────────
    reason: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="reportstatus"),
        nullable=False,
        default=ReportStatus.open,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # `foreign_keys=[reporter_id]` tells SQLAlchemy:
    # "Use the reporter_id column as the join key for this relationship."
    # Without this, SQLAlchemy sees two FKs pointing to users and raises
    # AmbiguousForeignKeysError.
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[reporter_id], back_populates="reports_made"
    )
    reported_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reported_user_id], back_populates="reports_received"
    )
    reported_job: Mapped["Job | None"] = relationship(
        "Job", back_populates="reports"
    )
