import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    JOB_SEEKER = "JOB_SEEKER"
    RECRUITER = "RECRUITER"
    ADMIN = "ADMIN"


class User(Base):
    """Mirrors the Prisma User model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
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
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="user", uselist=False, lazy="select"
    )
    recruiter: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile", back_populates="user", uselist=False, lazy="select"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", lazy="select"
    )
    reports_made: Mapped[list["Report"]] = relationship(
        "Report", foreign_keys="Report.reporter_id", back_populates="reporter", lazy="select"
    )
    reports_received: Mapped[list["Report"]] = relationship(
        "Report", foreign_keys="Report.reported_user_id", back_populates="reported_user", lazy="select"
    )
