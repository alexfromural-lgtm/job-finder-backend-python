# =============================================================================
# app/routers/queue.py  —  QUEUE TASK STATUS ENDPOINT
# =============================================================================
# When an operation is queued (apply, save), the client receives a `task_id`.
# This endpoint lets the client poll to find out if the task completed.
#
# GET /api/queue/job/{task_id} → { id, status, type?, result?, failedReason? }
#
# LEARNING CONCEPT ► Async Task Pattern (Celery + Redis)
#   1. Client: POST /api/jobseeker/apply/{job_id}
#      ← 202 Accepted: { queueJobId: "abc-task-id", status: "queued" }
#
#   2. Background: Celery worker picks up the task and runs it.
#
#   3. Client: GET /api/queue/job/abc-task-id  (every 2-3 seconds)
#      ← { id: "abc-task-id", status: "active" }   (while running)
#      ← { id: "abc-task-id", status: "completed", result: {...} }  (done!)
#      ← { id: "abc-task-id", status: "failed", failedReason: "..." }  (error)
#
# LEARNING CONCEPT ► State Mapping (Celery → User-friendly)
#   Celery uses its own state names (PENDING, STARTED, SUCCESS, FAILURE).
#   We map them to simpler "Bull-compatible" names (waiting, active, completed, failed)
#   because the React frontend was written against the Node.js Bull queue API.
#
# =============================================================================

from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.queue.celery_app import celery_app

router = APIRouter()

# =============================================================================
# STATE MAP
# =============================================================================
# Maps Celery's internal state names → human-readable status strings.
#
# LEARNING NOTE ► PENDING ambiguity
#   Celery returns PENDING both for "task is waiting in the queue" AND for
#   "task ID doesn't exist at all".  We treat both as "waiting" so the client
#   keeps polling instead of giving up.
# =============================================================================
_STATE_MAP = {
    "PENDING":  "waiting",   # in queue OR unknown task
    "RECEIVED": "waiting",   # broker acknowledged receipt
    "STARTED":  "active",    # worker is currently executing
    "SUCCESS":  "completed", # finished successfully
    "FAILURE":  "failed",    # raised an exception
    "RETRY":    "waiting",   # waiting for retry after failure
    "REVOKED":  "failed",    # task was cancelled
}

# Maps Celery task names → user-readable type labels.
# Mirrors Bull's job.data.type convention.
_TASK_TYPE_MAP = {
    "app.queue.tasks.apply_to_job": "apply-to-job",
    "app.queue.tasks.save_job":     "save-to-job",
}


@router.get("/job/{job_id}")
async def get_queue_job_status(job_id: str):
    """
    Poll the status of a queued Celery task.

    LEARNING EXAMPLE ► AsyncResult
      `AsyncResult(job_id, app=celery_app)` creates a handle to a task result
      stored in Redis.  It doesn't actually fetch anything until you read
      `result.state` or `result.result`.

    LEARNING NOTE ► result.info
      For tasks in STARTED state, Celery stores metadata in `result.info`.
      We read the task name from it to look up the user-readable type.
    """
    # Look up the task result in Redis.
    result: AsyncResult = AsyncResult(job_id, app=celery_app)

    # Map Celery state → frontend-friendly status string.
    # `.get(state, state.lower())` falls back to the raw state in lowercase.
    status = _STATE_MAP.get(result.state, result.state.lower())

    # Try to extract the task name from result metadata.
    task_name: str | None = None
    try:
        info = result.info  # dict for STARTED state; Exception object for FAILURE
        if isinstance(info, dict):
            task_name = info.get("name")
    except Exception:
        pass  # don't crash the status endpoint due to metadata issues

    # Build the response object incrementally.
    response: dict = {
        "id": job_id,
        "status": status,
    }

    # Add type only if we know it (from STARTED state metadata).
    if task_name and task_name in _TASK_TYPE_MAP:
        response["type"] = _TASK_TYPE_MAP[task_name]

    # Add result payload on success.
    # LEARNING NOTE ► result.result is the value returned by the task function.
    if result.state == "SUCCESS":
        response["result"] = result.result

    # Add error message on failure.
    # LEARNING NOTE ► result.result is the exception instance on failure.
    if result.state == "FAILURE":
        response["failedReason"] = str(result.result)

    return response
