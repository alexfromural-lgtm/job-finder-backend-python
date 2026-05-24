import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    """Mirrors the Prisma Job model."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    recruiter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("recruiter_profiles.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    requirements: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    salary_range: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
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

    # Performance indexes mirroring Prisma @@index directives
    __table_args__ = (
        Index("ix_jobs_is_active", "is_active"),
        Index("ix_jobs_is_active_category", "is_active", "category"),
        Index("ix_jobs_recruiter_created", "recruiter_id", "created_at"),
        Index("ix_jobs_is_active_created", "is_active", "created_at"),
    )
