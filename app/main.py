# =============================================================================
# app/main.py  —  APPLICATION ENTRY POINT
# =============================================================================
# This file is the "root" of the FastAPI application.  Every web framework
# needs one place that wires together: the HTTP server, middleware (extra
# processing layers), error handlers, and the route groups (routers).
#
# FastAPI equivalent of a Node/Express app.js / server.ts.
#
# LEARNING CONCEPT ► "Application factory pattern"
#   Instead of a bare script, we create an `app` object and configure it.
#   Other files import this object (or its sub-parts) rather than re-creating
#   everything from scratch.
#
# HOW TO RUN:
#   uvicorn app.main:app --reload   (development)
# =============================================================================

# -----------------------------------------------------------------------------
# 1. STANDARD-LIBRARY / THIRD-PARTY IMPORTS
# -----------------------------------------------------------------------------

# `asynccontextmanager` turns a plain generator function into an async context
# manager — used below to hook startup/shutdown events.
from contextlib import asynccontextmanager

# FastAPI is the web framework.  `FastAPI()` creates the ASGI application.
from fastapi import FastAPI

# CORSMiddleware solves the browser security rule that blocks JS from one
# origin (e.g. localhost:3000) calling an API on another (localhost:5002).
# CORS = Cross-Origin Resource Sharing.
from fastapi.middleware.cors import CORSMiddleware

# GZipMiddleware automatically compresses responses > a threshold, saving bandwidth.
from fastapi.middleware.gzip import GZipMiddleware

# slowapi is a rate-limiting library for FastAPI/Starlette.
#   Limiter        – the core object that tracks request counts per key.
#   _rate_limit_exceeded_handler – built-in 429 response when limit is hit.
#   RateLimitExceeded – the exception that fires when the limit is exceeded.
#   get_remote_address – helper that extracts the caller's IP from the request.
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# SQLAlchemy's exception for unique / foreign-key constraint violations.
from sqlalchemy.exc import IntegrityError

# -----------------------------------------------------------------------------
# 2. LOCAL IMPORTS  (our own modules)
# -----------------------------------------------------------------------------

# settings is a validated Pydantic object that reads from .env  (see config.py)
from app.config import settings

# AppError is our custom exception class — raised by services, caught here.
from app.errors.app_error import AppError

# Three global exception handlers (one per error type).
from app.middleware.error_handler import (
    app_error_handler,
    generic_error_handler,
    integrity_error_handler,
)

# Each router groups related endpoints together (auth, jobs, jobseeker, …).
from app.routers import auth, jobs, jobseeker, queue, recruiter

# Custom response class that converts snake_case keys → camelCase for the
# React frontend (e.g.  created_at  →  createdAt).
from app.utils.camel_response import CamelCaseJSONResponse

# =============================================================================
# 3. RATE LIMITER
# =============================================================================
# `key_func=get_remote_address` means: count requests per unique IP address.
# Example: if the limit is "5/minute", each IP gets 5 requests per minute.
#
# LEARNING EXAMPLE ► custom key function:
#   def by_user(request): return request.state.user_id  # limit per logged-in user
#   limiter = Limiter(key_func=by_user)
# =============================================================================
limiter = Limiter(key_func=get_remote_address)


# =============================================================================
# 4. LIFESPAN  (startup / shutdown hooks)
# =============================================================================
# FastAPI >= 0.93 uses a single `lifespan` async context manager instead of
# the deprecated @app.on_event("startup") / @app.on_event("shutdown").
#
# Code BEFORE the `yield` runs at startup.
# Code AFTER the `yield` runs at shutdown.
#
# LEARNING EXAMPLE ► opening a Redis connection pool at startup:
#   @asynccontextmanager
#   async def lifespan(app):
#       app.state.redis = await aioredis.create_redis_pool(REDIS_URL)
#       yield
#       app.state.redis.close()
#       await app.state.redis.wait_closed()
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    yield  # Nothing to do here — DB connections are managed per-request


# =============================================================================
# 5. APPLICATION FACTORY
# =============================================================================
# `FastAPI(...)` returns an ASGI application.  ASGI is the async equivalent of
# WSGI — it's the protocol that lets Python web frameworks talk to web servers
# like uvicorn or gunicorn.
#
# LEARNING TIP ► keyword arguments here become the OpenAPI/Swagger metadata.
# =============================================================================
app = FastAPI(
    title="Job Finder API",
    version="1.0.0",
    description="Job Finder REST API — Python/FastAPI port of the Node.js backend",
    # Every endpoint that returns a dict will use this response class.
    # It converts all dict keys from snake_case to camelCase automatically.
    default_response_class=CamelCaseJSONResponse,
    # Only expose /docs and /redoc in development to avoid leaking API details.
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# =============================================================================
# 6. ATTACH RATE LIMITER TO APP STATE
# =============================================================================
# `app.state` is a plain namespace for attaching arbitrary objects to the app.
# slowapi reads `app.state.limiter` automatically on each request.
# The exception handler maps RateLimitExceeded → HTTP 429 Too Many Requests.
# =============================================================================
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =============================================================================
# 7. MIDDLEWARE STACK
# =============================================================================
# Middleware wraps every request/response like layers of an onion.
# Order matters: middlewares added LAST run FIRST on the incoming request.
#
# LEARNING CONCEPT ► Middleware execution order (from outer to inner):
#   Request  → GZip → CORS → [route handler]
#   Response ← GZip ← CORS ← [route handler]
# =============================================================================

# GZip: compress responses >= 1 KB (saves bandwidth for large JSON payloads).
# Only active in production so local development isn't slowed by compression.
if settings.is_production:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS: tell browsers which origins are allowed to call this API.
# `allow_credentials=True` is required when the frontend sends cookies.
#
# LEARNING EXAMPLE ► multiple allowed origins:
#   cors_origins = ["https://myapp.com", "https://staging.myapp.com"]
cors_origins = [settings.CORS_ORIGIN] if settings.CORS_ORIGIN else (
    ["http://localhost:3000"] if settings.is_development else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # allow cookies / Authorization headers
    allow_methods=["*"],     # GET, POST, PUT, DELETE, PATCH, OPTIONS, …
    allow_headers=["*"],     # Content-Type, Authorization, etc.
)

# =============================================================================
# 8. GLOBAL EXCEPTION HANDLERS
# =============================================================================
# When an exception propagates out of a route handler, FastAPI checks these
# handlers in order.  The first matching type wins.
#
# LEARNING CONCEPT ► Exception hierarchy:
#   Exception  (most general — catches everything)
#   └─ IntegrityError   (database constraint violated)
#   └─ AppError         (our own structured error with an HTTP status code)
#
# Registration order doesn't matter here because each handler has a unique
# exception type.  But all handlers must be registered BEFORE routes so they
# are active when routes execute.
# =============================================================================
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# =============================================================================
# 9. ROUTERS
# =============================================================================
# `include_router` mounts a group of related endpoints at a URL prefix.
# `tags` groups endpoints in the auto-generated Swagger UI (/docs).
#
# LEARNING EXAMPLE ► the final URL is prefix + path defined in the router:
#   prefix="/api/auth"  +  @router.post("/login")  →  POST /api/auth/login
# =============================================================================
app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(jobseeker.router, prefix="/api/jobseeker", tags=["jobseeker"])
app.include_router(recruiter.router, prefix="/api/recruiter", tags=["recruiter"])
app.include_router(jobs.router,      prefix="/api/jobs",      tags=["jobs"])
app.include_router(queue.router,     prefix="/api/queue",     tags=["queue"])
