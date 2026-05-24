"""
Celery worker entry point.

Start with:
    celery -A app.queue.worker worker --loglevel=info

Mirrors the `[Worker] db-write-queue worker started` log line in worker.ts.
"""
from app.queue.celery_app import celery_app  # noqa: F401 — registers tasks via autodiscover
import app.queue.tasks  # noqa: F401 — ensure tasks are imported

from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(
    "[Worker] Celery job-queue worker starting (concurrency: %d)",
    settings.QUEUE_CONCURRENCY,
)
