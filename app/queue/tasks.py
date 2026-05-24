import asyncio
import logging
from typing import Optional

from app.queue.celery_app import celery_app
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.queue.tasks.apply_to_job",
    max_retries=3,
    default_retry_delay=0.5,  # initial delay in seconds; Celery uses exponential backoff
)
def apply_to_job_task(self, user_id: str, job_id: str, cover_letter: Optional[str] = None):
    """
    Async DB write task: submit a job application.
    Mirrors the "apply-to-job" case in queue/worker.ts.

    Retry policy: 3 attempts, exponential backoff starting at 500ms.
    """
    logger.info("[Worker] Processing apply-to-job | task_id=%s", self.request.id)

    async def _run():
        async with AsyncSessionLocal() as db:
            from app.services.jobseeker_service import apply_to_job
            application = await apply_to_job(db, user_id, job_id, cover_letter)
            return {
                "id": application.id,
                "job_id": application.job_id,
                "job_seeker_id": application.job_seeker_id,
                "status": application.status.value,
                "created_at": application.created_at.isoformat() if application.created_at else None,
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
        # Exponential backoff: 500ms, 1000ms, 2000ms
        delay = 0.5 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=delay)


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
                "id": saved.id,
                "job_id": saved.job_id,
                "job_seeker_id": saved.job_seeker_id,
                "saved_at": saved.saved_at.isoformat() if saved.saved_at else None,
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
