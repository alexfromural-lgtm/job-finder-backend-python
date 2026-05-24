from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.queue.celery_app import celery_app

router = APIRouter()

# Celery state → Bull-compatible status strings
_STATE_MAP = {
    "PENDING": "waiting",
    "RECEIVED": "waiting",
    "STARTED": "active",
    "SUCCESS": "completed",
    "FAILURE": "failed",
    "RETRY": "waiting",
    "REVOKED": "failed",
}

# Known task name → human-readable type (mirrors Bull job.data.type)
_TASK_TYPE_MAP = {
    "app.queue.tasks.apply_to_job": "apply-to-job",
    "app.queue.tasks.save_job": "save-to-job",
}


@router.get("/job/{job_id}")
async def get_queue_job_status(job_id: str):
    """
    Poll the status of a queued Celery task.

    Mirrors GET /api/queue/job/:jobId in queue.route.ts.
    Returns the same shape the React frontend expects:
      { id, type, status, result?, failedReason? }

    Status values (mapped from Celery → Bull equivalents):
      waiting | active | completed | failed
    """
    result: AsyncResult = AsyncResult(job_id, app=celery_app)

    # Celery returns PENDING for both "not found" and "genuinely waiting".
    # Since Celery doesn't write PENDING states to the backend on dispatch,
    # we return a 'waiting' status instead of a 404, so that polling continues.

    status = _STATE_MAP.get(result.state, result.state.lower())

    # Extract task name from result info when available
    task_name: str | None = None
    try:
        info = result.info  # dict with metadata for STARTED state
        if isinstance(info, dict):
            task_name = info.get("name")
    except Exception:
        pass

    response: dict = {
        "id": job_id,
        "status": status,
    }

    if task_name and task_name in _TASK_TYPE_MAP:
        response["type"] = _TASK_TYPE_MAP[task_name]

    if result.state == "SUCCESS":
        response["result"] = result.result

    if result.state == "FAILURE":
        response["failedReason"] = str(result.result)

    return response
