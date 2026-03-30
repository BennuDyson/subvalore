import logging
from typing import Any

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from app.services.ingestion import _build_session
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticker
from app.services.ingestion import fetch_raw, normalize
from app.services.ticker_service import (
    get_or_create_ticker,
    is_stale,
    store_all,
    read_all,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ticker"])


@router.get("/ticker/{symbol}/all")
def get_ticker_all(symbol: str, db: Session = Depends(get_db)) -> dict:
    """
    Return all financial datasets for a ticker.

    - Serves from PostgreSQL if data is fresh (< DATA_STALE_MINUTES old).
    - Fetches from yfinance, stores to DB, then serves if data is missing or stale.
    """
    symbol = symbol.upper()
    ticker = get_or_create_ticker(db, symbol)

    if is_stale(ticker):
        logger.info("[%s] Data stale/missing — fetching from yfinance.", symbol)
        try:
            raw = fetch_raw(symbol)
            norm = normalize(symbol, raw)
            store_all(db, ticker, norm)
            db.refresh(ticker)
        except Exception as exc:
            db.rollback()
            logger.error("[%s] yfinance fetch failed: %s", symbol, exc)
            if ticker.last_refreshed_at is None:
                # Never been stored — nothing to serve
                raise HTTPException(
                    status_code=502,
                    detail=f"Could not fetch data for '{symbol}'. Is it a valid ticker?",
                )
            # Serve stale data rather than hard-failing
            logger.warning("[%s] Serving stale data due to fetch error.", symbol)
    else:
        logger.info("[%s] Serving fresh data from DB.", symbol)

    return read_all(db, ticker)


@router.post("/ticker/{symbol}/refresh")
def refresh_ticker(symbol: str, db: Session = Depends(get_db)) -> dict:
    """
    Force a fresh fetch from yfinance regardless of data age.
    Updates all datasets in PostgreSQL and returns the refreshed data.
    """
    symbol = symbol.upper()
    ticker = get_or_create_ticker(db, symbol)

    logger.info("[%s] Forced refresh requested.", symbol)
    try:
        raw = fetch_raw(symbol)
        norm = normalize(symbol, raw)
        store_all(db, ticker, norm)
        db.refresh(ticker)
    except Exception as exc:
        db.rollback()
        logger.error("[%s] Forced refresh failed: %s", symbol, exc)
        raise HTTPException(status_code=502, detail=f"Refresh failed for '{symbol}': {exc}")

    return {
        "status": "ok",
        "symbol": symbol,
        "last_refreshed_at": ticker.last_refreshed_at.isoformat() if ticker.last_refreshed_at else None,
    }


@router.get("/ticker/{symbol}/status")
def get_ticker_status(symbol: str, db: Session = Depends(get_db)) -> dict:
    """
    Return metadata about a ticker in the DB:
    whether it exists, when it was last refreshed, and whether its data is stale.
    """
    symbol = symbol.upper()
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()

    if not ticker:
        return {
            "symbol": symbol,
            "exists": False,
            "company_name": None,
            "last_refreshed_at": None,
            "is_stale": True,
            "stale_threshold_minutes": settings.data_stale_minutes,
        }

    return {
        "symbol": symbol,
        "exists": True,
        "company_name": ticker.company_name,
        "last_refreshed_at": ticker.last_refreshed_at.isoformat() if ticker.last_refreshed_at else None,
        "is_stale": is_stale(ticker),
        "stale_threshold_minutes": settings.data_stale_minutes,
    }


@router.get("/debug/{symbol}", tags=["debug"])
def debug_yfinance(symbol: str) -> dict[str, Any]:
    """
    Raw yfinance diagnostic endpoint.
    Shows exactly what yfinance returns for each dataset — shapes, types, errors.
    Remove or restrict this endpoint in production.
    """
    symbol = symbol.upper()
    t = yf.Ticker(symbol, session=_build_session())
    report: dict[str, Any] = {}

    def probe(name: str, fn):
        try:
            val = fn()
            if val is None:
                return {"status": "none"}
            if hasattr(val, "shape"):          # DataFrame / Series
                return {"status": "ok", "type": type(val).__name__, "shape": list(val.shape), "columns": list(val.columns) if hasattr(val, "columns") else None, "sample": val.head(2).to_dict()}
            if isinstance(val, dict):
                return {"status": "ok", "type": "dict", "keys": list(val.keys())[:20], "len": len(val)}
            if isinstance(val, list):
                return {"status": "ok", "type": "list", "len": len(val), "sample": val[:2]}
            return {"status": "ok", "type": type(val).__name__, "value": str(val)[:200]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    report["info"]                       = probe("info",                       lambda: t.info)
    report["history_7d_1m"]              = probe("history",                    lambda: t.history(period="7d", interval="1m"))
    report["dividends"]                  = probe("dividends",                  lambda: t.dividends)
    report["income_stmt"]                = probe("income_stmt",                lambda: t.income_stmt)
    report["quarterly_income_stmt"]      = probe("quarterly_income_stmt",      lambda: t.quarterly_income_stmt)
    report["balance_sheet"]              = probe("balance_sheet",              lambda: t.get_balance_sheet(as_dict=False, pretty=False, freq="quarterly"))
    report["earnings_dates"]             = probe("earnings_dates",             lambda: t.earnings_dates)
    report["calendar"]                   = probe("calendar",                   lambda: t.calendar)
    report["recommendations"]            = probe("recommendations",            lambda: t.get_recommendations())
    report["analyst_price_targets"]      = probe("analyst_price_targets",      lambda: t.get_analyst_price_targets())
    report["earnings_estimate"]          = probe("earnings_estimate",          lambda: t.earnings_estimate)
    report["revenue_estimate"]           = probe("revenue_estimate",           lambda: t.revenue_estimate)
    report["eps_trend"]                  = probe("eps_trend",                  lambda: t.eps_trend)
    report["growth_estimates"]           = probe("growth_estimates",           lambda: t.growth_estimates)
    report["insider_purchases"]          = probe("insider_purchases",          lambda: t.insider_purchases)
    report["insider_transactions"]       = probe("insider_transactions",       lambda: t.insider_transactions)
    report["news"]                       = probe("news",                       lambda: t.news)

    return {"symbol": symbol, "yfinance_version": yf.__version__, "report": report}
