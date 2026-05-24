import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReportStatus(str, enum.Enum):
    open = "open"
    reviewed = "reviewed"
    dismissed = "dismissed"


class Report(Base):
    """Mirrors the Prisma Report model."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    reporter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    reported_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    reported_job_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="reportstatus"),
        nullable=False,
        default=ReportStatus.open,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User", foreign_keys=[reporter_id], back_populates="reports_made"
    )
    reported_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reported_user_id], back_populates="reports_received"
    )
    reported_job: Mapped["Job | None"] = relationship(
        "Job", back_populates="reports"
    )
