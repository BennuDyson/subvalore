from fastapi import APIRouter

from app.services.scheduler import get_status, trigger_now

router = APIRouter(tags=["scheduler"])


@router.get("/scheduler/status")
def scheduler_status() -> dict:
    """Return scheduler state: enabled, running, last run, next run."""
    return get_status()


@router.post("/scheduler/run-now")
def scheduler_run_now() -> dict:
    """Trigger an immediate full refresh of all tickers, outside the normal schedule."""
    trigger_now()
    return {"status": "triggered", "message": "Refresh job queued. Check /api/scheduler/status for progress."}
