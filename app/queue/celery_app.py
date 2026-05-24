from celery import Celery

from app.config import settings

# ---------------------------------------------------------------------------
# Celery app — mirrors Bull queue configuration in queue/queue.ts
#
# broker:  Redis (same REDIS_URL used by Bull)
# backend: Redis (keeps task results so /api/queue/job/:id can poll them,
#          equivalent to removeOnComplete: false in Bull)
# ---------------------------------------------------------------------------
celery_app = Celery(
    "job_finder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # Task result expiry — keep results for 7 days (same philosophy as Bull's
    # removeOnComplete: false — clients can poll long after completion)
    result_expires=7 * 24 * 60 * 60,

    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Retry policy mirrors Bull's defaultJobOptions:
    #   attempts: 3, backoff: { type: "exponential", delay: 500 }
    task_acks_late=True,            # acknowledge only after task completes
    task_reject_on_worker_lost=True,

    # Worker concurrency from env (mirrors QUEUE_CONCURRENCY)
    worker_concurrency=settings.QUEUE_CONCURRENCY,
)

# Auto-discover tasks in app.queue.tasks
celery_app.autodiscover_tasks(["app.queue"])
