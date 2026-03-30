"""
Background scheduler: refreshes all known tickers from yfinance
on a configurable interval (default: every 24 hours).

The scheduler runs in a daemon thread managed by APScheduler.
It starts with the FastAPI lifespan and stops cleanly on shutdown.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_last_run_at: datetime | None = None
_last_run_status: str = "never"


# ── Background job ────────────────────────────────────────────────────────────

def _refresh_all_job() -> None:
    """
    Iterate over every ticker in the DB and pull fresh data from yfinance.
    Runs in a background thread; uses its own DB session.
    """
    global _last_run_at, _last_run_status

    # Late imports to avoid circular dependencies at module load time
    from app.database import SessionLocal
    from app.models import Ticker
    from app.services.ingestion import fetch_raw, normalize
    from app.services.ticker_service import store_all

    _last_run_at = datetime.now(timezone.utc)
    logger.info("Scheduled refresh starting…")

    db = SessionLocal()
    try:
        tickers = db.query(Ticker).all()
        total = len(tickers)

        if total == 0:
            _last_run_status = "ok (no tickers in DB)"
            logger.info("No tickers to refresh.")
            return

        succeeded = failed = 0

        for ticker in tickers:
            try:
                raw = fetch_raw(ticker.symbol)
                norm = normalize(ticker.symbol, raw)
                store_all(db, ticker, norm)
                succeeded += 1
                logger.info("[%s] Scheduled refresh complete.", ticker.symbol)
            except Exception as exc:
                failed += 1
                logger.error("[%s] Scheduled refresh failed: %s", ticker.symbol, exc)

        _last_run_status = f"ok ({succeeded}/{total} succeeded, {failed} failed)"
        logger.info("Scheduled refresh done — %s", _last_run_status)

    except Exception as exc:
        _last_run_status = f"error: {exc}"
        logger.error("Scheduled refresh job crashed: %s", exc)
    finally:
        db.close()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    global _scheduler

    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false).")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _refresh_all_job,
        trigger=IntervalTrigger(hours=settings.refresh_interval_hours),
        id="refresh_all_tickers",
        name="Refresh all tickers from yfinance",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late if the server was briefly down
    )
    _scheduler.start()

    job = _scheduler.get_job("refresh_all_tickers")
    logger.info(
        "Scheduler started. Interval: every %dh. Next run: %s",
        settings.refresh_interval_hours,
        job.next_run_time if job else "unknown",
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ── Status helpers ────────────────────────────────────────────────────────────

def get_status() -> dict:
    job = _scheduler.get_job("refresh_all_tickers") if (_scheduler and _scheduler.running) else None
    return {
        "enabled": settings.scheduler_enabled,
        "running": bool(_scheduler and _scheduler.running),
        "refresh_interval_hours": settings.refresh_interval_hours,
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
        "last_run_status": _last_run_status,
        "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }


def trigger_now() -> None:
    """Kick off an immediate refresh outside the normal schedule."""
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("refresh_all_tickers")
        if job:
            job.modify(next_run_time=datetime.now(timezone.utc))
            logger.info("Immediate refresh triggered via scheduler.")
            return
    # Fallback: run synchronously if scheduler isn't running
    logger.info("Scheduler not running — executing refresh synchronously.")
    _refresh_all_job()
