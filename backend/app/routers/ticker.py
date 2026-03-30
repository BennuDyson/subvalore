import logging

from fastapi import APIRouter, Depends, HTTPException
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
