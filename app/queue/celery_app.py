# =============================================================================
# app/queue/celery_app.py  —  CELERY APPLICATION CONFIGURATION
# =============================================================================
# Celery is a distributed task queue for Python.
# It lets you run code OUTSIDE the HTTP request/response cycle — perfect for:
#   • Long-running operations (avoid 30s request timeouts)
#   • Background jobs (send emails, process images)
#   • Scheduled tasks (cron-like recurring jobs)
#   • Retry logic (automatically retry failed DB writes)
#
# ARCHITECTURE:
#   FastAPI app  →  Redis (broker)  →  Celery worker  →  PostgreSQL
#   "enqueue task"   "message queue"  "execute task"    "write data"
#
# LEARNING CONCEPT ► Broker vs Backend
#   Broker  → where TASKS are sent/queued (Redis here, could be RabbitMQ)
#             The worker listens here for new tasks.
#   Backend → where RESULTS are stored after completion
#             Used by the status endpoint to look up task outcomes.
#
# LEARNING CONCEPT ► Worker Process
#   Celery workers are SEPARATE PROCESSES from the FastAPI app.
#   They run continuously, waiting for tasks on the Redis queue.
#   Start workers with: celery -A app.queue.celery_app worker --loglevel=info
# =============================================================================

from celery import Celery
from app.config import settings

# =============================================================================
# CREATE CELERY APPLICATION
# =============================================================================
# `Celery(name, broker=..., backend=...)`:
#   name    → application name (used in task names and logs)
#   broker  → Redis URL where tasks are SENT
#   backend → Redis URL where results are STORED
#
# LEARNING NOTE ► same Redis for both broker and backend:
#   This is common for simple setups.  In high-traffic systems you might use
#   separate Redis instances to avoid interference.
# =============================================================================
celery_app = Celery(
    "job_finder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# =============================================================================
# CONFIGURATION
# =============================================================================
# `celery_app.conf.update(...)` sets Celery configuration options.
# =============================================================================
celery_app.conf.update(
    # ── Result Storage ────────────────────────────────────────────────────────
    # Keep task results in Redis for 7 days.
    # This allows the status endpoint to respond to polls long after completion.
    # (Without this, results are deleted immediately after the first read.)
    result_expires=7 * 24 * 60 * 60,  # 7 days in seconds

    # ── Serialization ────────────────────────────────────────────────────────
    # Tasks arguments and results are serialized as JSON.
    # JSON is safe, human-readable, and language-agnostic.
    # (Alternative: pickle — faster but can execute arbitrary code if data is tampered with)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],           # only accept JSON-serialized messages

    # ── Timezone ─────────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,

    # ── Reliability Settings ──────────────────────────────────────────────────
    # `task_acks_late=True`:
    #   "Acknowledge" (confirm receipt) AFTER the task completes, not before.
    #   If the worker crashes during a task, the task is re-queued automatically.
    #   Default is False (acknowledge on receipt) — that loses tasks on crash.
    task_acks_late=True,

    # If the worker process dies unexpectedly, reject the task so it's re-queued.
    task_reject_on_worker_lost=True,

    # How many tasks a single worker processes concurrently.
    # Configured via QUEUE_CONCURRENCY env var (default: 5).
    worker_concurrency=settings.QUEUE_CONCURRENCY,
)

# =============================================================================
# TASK DISCOVERY
# =============================================================================
# `autodiscover_tasks` scans the given packages for `@celery_app.task` decorators.
# This means we don't have to manually import every task module — Celery finds them.
#
# LEARNING EXAMPLE ► manual import alternative (if autodiscover is disabled):
#   from app.queue import tasks   # just importing is enough to register tasks
# =============================================================================
celery_app.autodiscover_tasks(["app.queue"])
