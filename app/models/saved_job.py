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
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False
    )
    job_seeker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_seeker_profiles.id"), nullable=False
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="saved_by")
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="saved_jobs"
    )

    # Unique constraint: a job seeker can save a job only once
    __table_args__ = (
        UniqueConstraint("job_id", "job_seeker_id", name="uq_saved_jobs_job_jobseeker"),
    )
