# =============================================================================
# app/models/user.py  —  USER DATABASE MODEL
# =============================================================================
# This file defines the SQLAlchemy ORM model for the `users` table.
# It maps the Python `User` class to database rows — each attribute
# corresponds to a column, and each instance represents one row.
#
# LEARNING CONCEPT ► SQLAlchemy ORM Models
#   An ORM model is a class where:
#     • The class itself → a database table
#     • Each class attribute → a column in that table
#     • Each instance of the class → a row in that table
#
#   EXAMPLE:
#     user = User(name="Alice", email="alice@example.com", ...)
#     db.add(user)         # stages INSERT
#     await db.commit()    # executes INSERT in the DB
#     print(user.id)       # reads the generated UUID
#
# LEARNING CONCEPT ► Enum types
#   `enum.Enum` lets you define a fixed set of allowed string values.
#   Using Enum instead of plain strings prevents typos and invalid values.
#
#   EXAMPLE:
#     Role.JOB_SEEKER.value  → "JOB_SEEKER"
#     user.roles = [Role.RECRUITER]
# =============================================================================

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
# PostgreSQL-specific types:
#   ARRAY  → PostgreSQL native array column (e.g. TEXT[])
#   UUID   → PostgreSQL native UUID type
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# =============================================================================
# ROLE ENUM
# =============================================================================
# `str, enum.Enum` makes Role members both Enum values AND strings.
# This means Role.JOB_SEEKER == "JOB_SEEKER" evaluates to True, which
# simplifies comparisons like `if "JOB_SEEKER" in user.roles`.
#
# LEARNING EXAMPLE:
#   class Color(str, enum.Enum):
#       RED = "red"
#       BLUE = "blue"
#   Color.RED == "red"   → True
#   f"Color: {Color.RED}"  → "Color: red"  (uses the string value)
# =============================================================================
class Role(str, enum.Enum):
    JOB_SEEKER = "JOB_SEEKER"
    RECRUITER  = "RECRUITER"
    ADMIN      = "ADMIN"


# =============================================================================
# USER MODEL
# =============================================================================
# `__tablename__` tells SQLAlchemy which database table this class maps to.
#
# `Mapped[type]` is a type hint that works with SQLAlchemy's new 2.0 API:
#   Mapped[str]        → non-nullable string column
#   Mapped[str | None] → nullable string column
#   Mapped[bool]       → non-nullable boolean column
#
# `mapped_column(...)` configures the column's SQL attributes.
# =============================================================================
class User(Base):
    """Mirrors the Prisma User model."""

    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────────────────────
    # UUID = Universally Unique Identifier (128-bit random ID).
    # `as_uuid=False` stores it as a plain string instead of Python's uuid.UUID
    # object — more compatible with how the Node.js side treats it.
    # `default=lambda: str(uuid.uuid4())` generates a new UUID in Python
    # BEFORE inserting — avoids a round-trip to get the DB-generated ID.
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Basic Fields ─────────────────────────────────────────────────────────
    name:     Mapped[str]  = mapped_column(String, nullable=False)
    email:    Mapped[str]  = mapped_column(String, unique=True, nullable=False)  # UNIQUE index
    password: Mapped[str]  = mapped_column(String, nullable=False)               # bcrypt hash

    # ── Roles Array ───────────────────────────────────────────────────────────
    # PostgreSQL ARRAY(String) stores multiple values in a single column.
    # e.g. ["JOB_SEEKER", "RECRUITER"] for a user who upgraded their account.
    # `default=list` creates an empty list [] for new users.
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    # `server_default=func.now()` → PostgreSQL sets this to NOW() on INSERT.
    # `onupdate=func.now()`       → PostgreSQL updates this on every UPDATE.
    # `DateTime(timezone=True)`   → stores timezone-aware timestamps (UTC).
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
    # `relationship(...)` tells SQLAlchemy how tables are connected.
    # It does NOT create a column — it creates a Python attribute that
    # loads related objects via a JOIN or sub-query.
    #
    # `back_populates` creates a two-way link:
    #   user.job_seeker      → the JobSeekerProfile for this user
    #   profile.user         → the User for this profile
    #
    # `uselist=False` → one-to-one (a user has ONE job seeker profile)
    # `uselist=True`  → one-to-many (a user has MANY notifications) [default]
    #
    # `lazy="select"` → only load this relationship when you explicitly access it
    # (not automatically with every User query — avoids N+1 query problems)
    #
    # LEARNING EXAMPLE ► accessing relationships:
    #   user = await db.get(User, user_id)
    #   # This triggers an additional SELECT to load the profile:
    #   await db.refresh(user, ["job_seeker"])
    #   print(user.job_seeker.bio)
    job_seeker: Mapped["JobSeekerProfile"] = relationship(
        "JobSeekerProfile", back_populates="user", uselist=False, lazy="select"
    )
    recruiter: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile", back_populates="user", uselist=False, lazy="select"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", lazy="select"
    )
    # `foreign_keys` disambiguates when multiple foreign keys point to the same table.
    # Report has reporter_id AND reported_user_id — both point to users.
    reports_made: Mapped[list["Report"]] = relationship(
        "Report", foreign_keys="Report.reporter_id", back_populates="reporter", lazy="select"
    )
    reports_received: Mapped[list["Report"]] = relationship(
        "Report", foreign_keys="Report.reported_user_id", back_populates="reported_user", lazy="select"
    )
