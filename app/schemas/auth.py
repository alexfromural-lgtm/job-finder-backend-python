# =============================================================================
# app/schemas/auth.py  —  REQUEST VALIDATION SCHEMAS FOR AUTH ENDPOINTS
# =============================================================================
# Schemas are Pydantic models that describe the shape of incoming JSON bodies.
# FastAPI automatically:
#   1. Parses the incoming JSON into the schema class.
#   2. Validates all fields (types, constraints, validators).
#   3. Returns HTTP 422 Unprocessable Entity if validation fails.
#
# LEARNING CONCEPT ► Pydantic vs SQLAlchemy Models
#   SQLAlchemy models  → describe the DATABASE STRUCTURE (tables, columns).
#   Pydantic schemas   → describe API INPUT/OUTPUT (what JSON the client sends).
#
#   They look similar but serve different purposes:
#     class User(Base):        # SQLAlchemy: creates a "users" table
#         __tablename__ = "users"
#         id = Column(...)
#
#     class SignupSchema(BaseModel):  # Pydantic: validates incoming JSON
#         email: str
#         password: str
#
# LEARNING CONCEPT ► Field Validators
#   `@field_validator("field_name")` decorates a class method that runs
#   AFTER the type check and can apply additional business rules.
#
#   EXAMPLE:
#     @field_validator("password")
#     @classmethod
#     def strong_password(cls, v):
#         if len(v) < 8:
#             raise ValueError("Too short")  # → 422 error with this message
#         return v  # must return the (possibly modified) value
#
# LEARNING CONCEPT ► EmailStr
#   `pydantic[email]` provides `EmailStr` — a string that validates email
#   format.  "notanemail" → validation error; "alice@example.com" → passes.
# =============================================================================

from pydantic import BaseModel, EmailStr, field_validator


# =============================================================================
# LoginSchema
# =============================================================================
# Used by POST /api/auth/login.
# Validates that the email is a valid format and the password is >= 8 chars.
#
# LEARNING EXAMPLE ► what FastAPI does automatically:
#   POST /api/auth/login  {"email": "bad", "password": "short"}
#   → 422 Unprocessable Entity
#     {"detail": [{"loc": ["body", "email"], "msg": "value is not a valid email"}, ...]}
# =============================================================================
class LoginSchema(BaseModel):
    """Mirrors loginSchema (auth.schema.ts)."""

    email: EmailStr  # validates email format automatically
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# =============================================================================
# SignupSchema
# =============================================================================
# Used by POST /api/auth/signup/jobseeker.
# Adds `name` to the login fields and validates it's not empty/whitespace.
#
# LEARNING NOTE ► `v.strip()` removes leading/trailing whitespace.
#   "  " (spaces only) → strip() → "" → falsy → validation error
#   "Alice" → strip() → "Alice" → truthy → passes
# =============================================================================
class SignupSchema(BaseModel):
    """Mirrors signupSchema (jobseeker.schema.ts)."""

    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name is required")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
