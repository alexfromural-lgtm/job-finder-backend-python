from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.errors.app_error import AppError
from app.middleware.error_handler import (
    app_error_handler,
    generic_error_handler,
    integrity_error_handler,
)
from app.routers import auth, jobs, jobseeker, queue, recruiter

# ---------------------------------------------------------------------------
# Rate limiter (mirrors express-rate-limit in auth.route.ts)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    yield  # Nothing to do here — DB connections are managed per-request


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Job Finder API",
    version="1.0.0",
    description="Job Finder REST API — Python/FastAPI port of the Node.js backend",
    # Disable auto docs in production (optional — comment out if you want Swagger)
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Rate limiter state
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Security middleware — mirrors helmet() + compression()
# ---------------------------------------------------------------------------
if settings.is_production:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# CORS — mirrors cors({ origin: CORS_ORIGIN, credentials: true })
# ---------------------------------------------------------------------------
cors_origins = [settings.CORS_ORIGIN] if settings.CORS_ORIGIN else (
    ["http://localhost:3000"] if settings.is_development else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers — mirrors errorHandler.middleware.ts
# Must be registered BEFORE routes
# ---------------------------------------------------------------------------
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ---------------------------------------------------------------------------
# Routers — same URL prefixes as the Node.js app
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobseeker.router, prefix="/api/jobseeker", tags=["jobseeker"])
app.include_router(recruiter.router, prefix="/api/recruiter", tags=["recruiter"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
