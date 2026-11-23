# =============================================================================
# app/queue/tasks.py  —  CELERY TASK DEFINITIONS
# =============================================================================
# Tasks are the actual functions that Celery workers execute.
# They are registered with the `@celery_app.task(...)` decorator.
#
# KEY CHALLENGE: Celery workers are SYNCHRONOUS Python processes,
# but our database layer is ASYNC (asyncio / asyncpg / SQLAlchemy async).
#
# Solution: use `asyncio.get_event_loop().run_until_complete(coroutine)`
# to run an async function from a synchronous context.
#
# LEARNING CONCEPT ► Sync vs Async in Celery
#   FastAPI is async — route handlers use `async def` and `await`.
#   Celery workers are sync  — task functions use regular `def`.
#   The bridge is `asyncio.run()` or `loop.run_until_complete()`.
#
# LEARNING CONCEPT ► Retry with Exponential Backoff
#   If a task fails (e.g., DB connection error), Celery can retry it.
#   Exponential backoff means each retry waits longer:
#     Attempt 1: fail → wait 0.5s
#     Attempt 2: fail → wait 1.0s   (0.5 * 2^1)
#     Attempt 3: fail → wait 2.0s   (0.5 * 2^2)
#     Give up after max_retries=3
# =============================================================================

import asyncio
import logging
from typing import Optional

from app.queue.celery_app import celery_app
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: run async code from sync context
# =============================================================================
# `asyncio.get_event_loop().run_until_complete(coro)`:
#   - Gets the current event loop (or creates one)
#   - Runs the coroutine `coro` to completion synchronously
#   - Returns the coroutine's return value
#
# LEARNING NOTE ► why not `asyncio.run()`?
#   `asyncio.run()` creates a NEW event loop each call.  On some platforms
#   this causes issues when called from within an already-running event loop.
#   `get_event_loop().run_until_complete()` is safer for Celery worker threads.
# =============================================================================
def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# TASK 1: apply_to_job_task
# =============================================================================
# `@celery_app.task(bind=True, ...)` registers this function as a Celery task.
#   bind=True      → adds `self` as the first argument so we can call
#                    `self.retry(...)` to retry the task.
#   name="..."     → explicit task name for the queue router to identify it.
#   max_retries=3  → try at most 3 times before giving up.
#   default_retry_delay=0.5  → first retry after 0.5 seconds.
#
# DISPATCH FROM ROUTER:
#   task = apply_to_job_task.delay(user_id, job_id, cover_letter)
#   returns immediately with task.id
#
# EXECUTION BY WORKER:
#   The worker calls: apply_to_job_task(self, user_id, job_id, cover_letter)
# =============================================================================
@celery_app.task(
    bind=True,
    name="app.queue.tasks.apply_to_job",
    max_retries=3,
    default_retry_delay=0.5,
)
def apply_to_job_task(self, user_id: str, job_id: str, cover_letter: Optional[str] = None):
    """
    Async DB write task: submit a job application.
    Mirrors the "apply-to-job" case in queue/worker.ts.

    Retry policy: 3 attempts, exponential backoff starting at 500ms.

    LEARNING NOTE ► why is this in the queue?
      Applying for a job might also trigger:
        • A notification to the recruiter
        • An email to the applicant
        • Analytics logging
      Doing all this synchronously in an HTTP handler would be slow.
      The queue handles it without blocking the user.
    """
    logger.info("[Worker] Processing apply-to-job | task_id=%s", self.request.id)

    # `_run()` is an inner async function that does the actual DB work.
    # We define it inside the task so it closes over `user_id`, `job_id`, etc.
    async def _run():
        # `AsyncSessionLocal()` creates a DB session for this task.
        # Using `async with` ensures the session is closed even if an error occurs.
        async with AsyncSessionLocal() as db:
            # Import inside the function to avoid circular imports at module level.
            from app.services.jobseeker_service import apply_to_job
            application = await apply_to_job(db, user_id, job_id, cover_letter)
            # Return a serialisable dict (not the SQLAlchemy object itself).
            return {
                "id":           application.id,
                "job_id":       application.job_id,
                "job_seeker_id": application.job_seeker_id,
                "status":       application.status.value,
                "created_at":   application.created_at.isoformat() if application.created_at else None,
            }

    try:
        result = _run_async(_run())
        logger.info("[Worker] apply-to-job completed | task_id=%s", self.request.id)
        return result
    except Exception as exc:
        logger.error(
            "[Worker] apply-to-job failed | task_id=%s | attempt=%d | error=%s",
            self.request.id,
            self.request.retries + 1,
            str(exc),
        )
        # `self.retry(exc=exc, countdown=delay)` re-queues the task after `delay` seconds.
        # `self.request.retries` is 0 on first failure, 1 on second, etc.
        # `raise self.retry(...)` — the raise is important! Without it, Celery
        # would think the task SUCCEEDED instead of scheduling a retry.
        delay = 0.5 * (2 ** self.request.retries)  # 0.5, 1.0, 2.0 seconds
        raise self.retry(exc=exc, countdown=delay)


# =============================================================================
# TASK 2: save_job_task
# =============================================================================
# Same pattern as apply_to_job_task.
# Saves a job to the job seeker's bookmark list.
# =============================================================================
@celery_app.task(
    bind=True,
    name="app.queue.tasks.save_job",
    max_retries=3,
    default_retry_delay=0.5,
)
def save_job_task(self, user_id: str, job_id: str):
    """
    Async DB write task: save a job for a job seeker.
    Mirrors the "save-job" case in queue/worker.ts.
    """
    logger.info("[Worker] Processing save-job | task_id=%s", self.request.id)

    async def _run():
        async with AsyncSessionLocal() as db:
            from app.services.jobseeker_service import save_job
            saved = await save_job(db, user_id, job_id)
            return {
                "id":           saved.id,
                "job_id":       saved.job_id,
                "job_seeker_id": saved.job_seeker_id,
                "saved_at":     saved.saved_at.isoformat() if saved.saved_at else None,
            }

    try:
        result = _run_async(_run())
        logger.info("[Worker] save-job completed | task_id=%s", self.request.id)
        return result
    except Exception as exc:
        logger.error(
            "[Worker] save-job failed | task_id=%s | attempt=%d | error=%s",
            self.request.id,
            self.request.retries + 1,
            str(exc),
        )
        delay = 0.5 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=delay)
