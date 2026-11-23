# =============================================================================
# app/models/notification.py  —  NOTIFICATION MODEL
# =============================================================================
# Notifications are messages sent to users about events (application status
# changes, system alerts, etc.).
#
# LEARNING CONCEPT ► Simple One-to-Many Relationship
#   One User can have MANY Notifications.
#   Each Notification belongs to exactly ONE User.
#   The `user_id` foreign key stores which user owns this notification.
#
# LEARNING NOTE ► No `updated_at` column
#   Notifications are immutable after creation — you can only mark them as
#   read (is_read) but never change their content.  So we have only
#   `created_at`, not `updated_at`.
# =============================================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# =============================================================================
# NOTIFICATION TYPE ENUM
# =============================================================================
# Two types of notifications:
#   application_update → triggered when a recruiter updates an application status
#   system             → platform-wide messages (maintenance, announcements)
#
# LEARNING EXAMPLE ► checking type in service code:
#   if notification.type == NotificationType.application_update:
#       # Notify user their application status changed
# =============================================================================
class NotificationType(str, enum.Enum):
    application_update = "application_update"
    system             = "system"


# =============================================================================
# NOTIFICATION MODEL
# =============================================================================
class Notification(Base):
    """Mirrors the Prisma Notification model."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Which user receives this notification
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notificationtype"), nullable=False
    )

    # `default=False` → notifications start unread.
    # Set to True when the user opens/reads it.
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Navigate from Notification → User:  notification.user.name
    # Navigate from User → Notifications: user.notifications (list)
    user: Mapped["User"] = relationship("User", back_populates="notifications")
