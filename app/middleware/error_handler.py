import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.errors.app_error import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle structured AppErrors from services."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


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
