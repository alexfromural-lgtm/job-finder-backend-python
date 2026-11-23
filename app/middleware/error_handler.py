# =============================================================================
# app/middleware/error_handler.py  —  GLOBAL EXCEPTION HANDLERS
# =============================================================================
# FastAPI allows registering "exception handlers" — async functions that run
# whenever a specific exception type escapes from a route handler.
#
# These handlers centralise error formatting so every route just raises an
# exception and trusts the handler to send the correct HTTP response.
#
# REGISTERED IN: app/main.py via app.add_exception_handler(...)
#
# LEARNING CONCEPT ► Exception Handler Signature
#   Every handler must accept (request, exc) and return a Response:
#
#   async def my_handler(request: Request, exc: MyError) -> Response:
#       return JSONResponse(status_code=..., content={...})
#
# LEARNING CONCEPT ► Handler priority
#   FastAPI checks handlers from most-specific to most-general.
#   AppError handler fires first (most specific), then Exception (catch-all).
# =============================================================================

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.errors.app_error import AppError

# `__name__` resolves to "app.middleware.error_handler" — this lets log
# messages include the module they came from.
logger = logging.getLogger(__name__)


# =============================================================================
# HANDLER 1: AppError  (our structured application errors)
# =============================================================================
# When service code raises AppError("User not found", 404), this handler
# converts it to:  HTTP 404  {"error": "User not found"}
#
# LEARNING EXAMPLE ► what the client receives:
#   raise AppError("Email already registered", 409)
#   → HTTP 409 Conflict
#   → { "error": "Email already registered" }
# =============================================================================
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle structured AppErrors from services."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


# =============================================================================
# HANDLER 2: IntegrityError  (database constraint violations)
# =============================================================================
# `IntegrityError` is raised by SQLAlchemy when a database constraint fails:
#   • UNIQUE constraint (inserting a duplicate email address)
#   • FOREIGN KEY constraint (referencing a non-existent record)
#   • NOT NULL constraint (omitting a required column)
#
# This handler specifically detects UNIQUE violations and returns HTTP 409.
# Everything else becomes HTTP 500.
#
# LEARNING EXAMPLE ► Prisma equivalent:
#   The original Node.js code checked `error.code === "P2002"` (Prisma's
#   unique-violation code).  Here we inspect the raw database error string.
#
# LEARNING NOTE ► `orig` attribute
#   SQLAlchemy wraps the low-level driver exception in `exc.orig`.
#   For asyncpg, `str(exc.orig)` contains "unique" for unique violations.
# =============================================================================
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handle SQLAlchemy unique constraint violations (equivalent to Prisma P2002).
    Mirrors the P2002 branch in errorHandler.middleware.ts.
    """
    orig = str(getattr(exc, "orig", ""))
    if "unique" in orig.lower() or "duplicate" in orig.lower():
        return JSONResponse(
            status_code=409,
            content={"error": "A record with that value already exists."},
        )
    logger.error("[Unhandled IntegrityError] %s", exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# =============================================================================
# HANDLER 3: Exception  (catch-all for unexpected errors)
# =============================================================================
# This is the last line of defence.  Any exception not caught by the handlers
# above ends up here.
#
# IMPORTANT SECURITY RULE: never expose raw exception messages to the client —
# they may contain stack traces, SQL queries, or config values.
# We log the full details server-side and return a generic message.
#
# SPECIAL CASE: JWT errors from python-jose bubble up as plain `Exception`
# (not JWTError) in some code paths.  We detect them by message content and
# return 401 instead of 500.
#
# LEARNING EXAMPLE ► the logger call:
#   logger.error("...", exc, exc_info=True)
#     ↑ exc_info=True appends the full traceback to the log entry.
# =============================================================================
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.
    Logs server-side and returns a safe 500.
    Mirrors the final else-branch of errorHandler.middleware.ts.
    """
    msg = str(exc)

    # JWT errors from python-jose surface as plain Exception with these messages
    if any(kw in msg for kw in ("Signature has expired", "invalid token", "Not enough segments")):
        return JSONResponse(status_code=401, content={"error": msg})

    logger.error("[Unhandled Error] %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
