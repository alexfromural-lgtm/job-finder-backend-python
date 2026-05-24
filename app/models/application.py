import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApplicationStatus(str, enum.Enum):
    submitted = "submitted"
    shortlisted = "shortlisted"
    rejected = "rejected"
    under_review = "under_review"


class Application(Base):
    """Mirrors the Prisma Application model."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False
    )
    job_seeker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_seeker_profiles.id"), nullable=False
    )
    cover_letter: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
        default=ApplicationStatus.submitted,
    )
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
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="applications"
    )
