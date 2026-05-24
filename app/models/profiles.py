import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobSeekerProfile(Base):
    """Mirrors the Prisma JobSeekerProfile model."""

    __tablename__ = "job_seeker_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False
    )
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    education: Mapped[str | None] = mapped_column(String, nullable=True)
    experience: Mapped[str | None] = mapped_column(String, nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_seeker")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job_seeker", lazy="select"
    )
    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="job_seeker", lazy="select"
    )


class RecruiterProfile(Base):
    """Mirrors the Prisma RecruiterProfile model."""

    __tablename__ = "recruiter_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    company_website: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recruiter")
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="recruiter", lazy="select"
    )
