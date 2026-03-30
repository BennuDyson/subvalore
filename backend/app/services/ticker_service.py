"""
Ticker service: DB read / write operations.
All SQL lives here; routers stay thin.
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Ticker,
    TickerMetrics,
    PriceHistory,
    DividendHistory,
    DatasetStore,
    TickerNews,
    TickerRecommendation,
    TickerPriceTarget,
)

logger = logging.getLogger(__name__)

# All dataset_type keys that live in dataset_store
DATASET_STORE_KEYS = [
    "income_statement",
    "quarterly_income_statement",
    "balance_sheet",
    "earnings_dates",
    "calendar",
    "earnings_estimate",
    "revenue_estimate",
    "eps_trend",
    "growth_estimates",
    "insider_purchases",
    "insider_transactions",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        import math
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _parse_dt(v: Any) -> datetime | None:
    """Parse an ISO string or datetime into a timezone-aware datetime."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _parse_date(v: Any) -> date | None:
    """Parse an ISO string or date into a date."""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


# ── Public API ───────────────────────────────────────────────────────────────

def get_or_create_ticker(db: Session, symbol: str) -> Ticker:
    symbol = symbol.upper()
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        ticker = Ticker(symbol=symbol)
        db.add(ticker)
        db.flush()
    return ticker


def is_stale(ticker: Ticker) -> bool:
    if ticker.last_refreshed_at is None:
        return True
    threshold = timedelta(minutes=settings.data_stale_minutes)
    now = datetime.now(timezone.utc)
    last = ticker.last_refreshed_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) > threshold


def store_all(db: Session, ticker: Ticker, normalized: dict[str, Any]) -> None:
    """Write all normalized data into PostgreSQL for the given ticker."""

    # ── Ticker metadata ───────────────────────────────────────────────────────
    ticker.company_name = normalized.get("company_name")
    ticker.last_refreshed_at = datetime.now(timezone.utc)

    # ── Scalar metrics ────────────────────────────────────────────────────────
    metrics = db.query(TickerMetrics).filter(TickerMetrics.ticker_id == ticker.id).first()
    if not metrics:
        metrics = TickerMetrics(ticker_id=ticker.id)
        db.add(metrics)
    metrics.pe = _safe_float(normalized.get("pe"))
    metrics.dividend_yield = _safe_float(normalized.get("dividend_yield"))
    metrics.market_cap = _safe_int(normalized.get("market_cap"))
    metrics.volume = _safe_int(normalized.get("volume"))
    metrics.volume_avg = _safe_int(normalized.get("volume_avg"))
    metrics.volume_avg_10 = _safe_int(normalized.get("volume_avg_10"))
    metrics.as_of = datetime.now(timezone.utc)

    # ── Price history (replace) ───────────────────────────────────────────────
    db.query(PriceHistory).filter(PriceHistory.ticker_id == ticker.id).delete()
    for row in (normalized.get("price_history") or []):
        # After reset_index(), intraday index column is "Datetime", daily is "Date"
        ts = _parse_dt(
            row.get("Datetime") or row.get("Date") or row.get("date") or row.get("timestamp")
        )
        if ts is None:
            continue
        db.add(PriceHistory(
            ticker_id=ticker.id,
            timestamp=ts,
            open=_safe_float(row.get("Open") or row.get("open")),
            high=_safe_float(row.get("High") or row.get("high")),
            low=_safe_float(row.get("Low") or row.get("low")),
            close=_safe_float(row.get("Close") or row.get("close")),
            volume=_safe_int(row.get("Volume") or row.get("volume")),
            dividends=_safe_float(row.get("Dividends") or row.get("dividends")),
            stock_splits=_safe_float(row.get("Stock Splits") or row.get("stock_splits")),
        ))

    # ── Dividend history (replace) ────────────────────────────────────────────
    db.query(DividendHistory).filter(DividendHistory.ticker_id == ticker.id).delete()
    for row in (normalized.get("dividend_history") or []):
        d = _parse_date(row.get("date"))
        if d is None:
            continue
        db.add(DividendHistory(
            ticker_id=ticker.id,
            date=d,
            value=_safe_float(row.get("value")),
        ))

    # ── Dataset store (JSONB, upsert per type) ────────────────────────────────
    for key in DATASET_STORE_KEYS:
        payload = normalized.get(key)
        ds = (
            db.query(DatasetStore)
            .filter(DatasetStore.ticker_id == ticker.id, DatasetStore.dataset_type == key)
            .first()
        )
        if not ds:
            ds = DatasetStore(ticker_id=ticker.id, dataset_type=key)
            db.add(ds)
        ds.payload = payload

    # ── News (replace) ────────────────────────────────────────────────────────
    db.query(TickerNews).filter(TickerNews.ticker_id == ticker.id).delete()
    for item in (normalized.get("news") or []):
        db.add(TickerNews(
            ticker_id=ticker.id,
            news_id=item.get("news_id"),
            title=item.get("title"),
            publisher=item.get("publisher"),
            published_at=_parse_dt(item.get("published_at")),
            url=item.get("url"),
            summary=item.get("summary"),
            raw_json=item.get("raw_json"),
        ))

    # ── Recommendations (replace) ─────────────────────────────────────────────
    db.query(TickerRecommendation).filter(TickerRecommendation.ticker_id == ticker.id).delete()
    for row in (normalized.get("recommendations") or []):
        # yfinance uses camelCase; after reset_index() period col may be "index" or "period"
        period = row.get("period") or row.get("Period") or str(row.get("index", ""))
        db.add(TickerRecommendation(
            ticker_id=ticker.id,
            period=period or None,
            strong_buy=_safe_int(row.get("strongBuy") or row.get("strong_buy")),
            buy=_safe_int(row.get("buy") or row.get("Buy")),
            hold=_safe_int(row.get("hold") or row.get("Hold")),
            sell=_safe_int(row.get("sell") or row.get("Sell")),
            strong_sell=_safe_int(row.get("strongSell") or row.get("strong_sell")),
        ))

    # ── Price targets (replace) ───────────────────────────────────────────────
    db.query(TickerPriceTarget).filter(TickerPriceTarget.ticker_id == ticker.id).delete()
    pt = normalized.get("price_targets")
    if pt:
        db.add(TickerPriceTarget(
            ticker_id=ticker.id,
            current=_safe_float(pt.get("current") or pt.get("currentPrice")),
            low=_safe_float(pt.get("low") or pt.get("targetLowPrice")),
            high=_safe_float(pt.get("high") or pt.get("targetHighPrice")),
            mean=_safe_float(pt.get("mean") or pt.get("targetMeanPrice")),
            median=_safe_float(pt.get("median") or pt.get("targetMedianPrice")),
        ))

    db.commit()
    logger.info("[%s] Stored all datasets to DB.", ticker.symbol)


def read_all(db: Session, ticker: Ticker) -> dict[str, Any]:
    """Read all stored data for a ticker and return an API-ready dict."""

    metrics = db.query(TickerMetrics).filter(TickerMetrics.ticker_id == ticker.id).first()

    ph_rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.ticker_id == ticker.id)
        .order_by(PriceHistory.timestamp)
        .all()
    )

    dh_rows = (
        db.query(DividendHistory)
        .filter(DividendHistory.ticker_id == ticker.id)
        .order_by(DividendHistory.date)
        .all()
    )

    ds_map: dict[str, Any] = {
        row.dataset_type: row.payload
        for row in db.query(DatasetStore).filter(DatasetStore.ticker_id == ticker.id).all()
    }

    news_rows = (
        db.query(TickerNews)
        .filter(TickerNews.ticker_id == ticker.id)
        .order_by(TickerNews.published_at.desc().nullslast())
        .all()
    )

    rec_rows = db.query(TickerRecommendation).filter(TickerRecommendation.ticker_id == ticker.id).all()

    pt_row = db.query(TickerPriceTarget).filter(TickerPriceTarget.ticker_id == ticker.id).first()

    return {
        "symbol": ticker.symbol,
        "company_name": ticker.company_name,
        "last_refreshed_at": ticker.last_refreshed_at.isoformat() if ticker.last_refreshed_at else None,

        "metrics": {
            "pe":           float(metrics.pe) if metrics and metrics.pe is not None else None,
            "dividend_yield": float(metrics.dividend_yield) if metrics and metrics.dividend_yield is not None else None,
            "market_cap":   metrics.market_cap if metrics else None,
            "volume":       metrics.volume if metrics else None,
            "volume_avg":   metrics.volume_avg if metrics else None,
            "volume_avg_10": metrics.volume_avg_10 if metrics else None,
        } if metrics else None,

        "price_history": [
            {
                "timestamp":   row.timestamp.isoformat() if row.timestamp else None,
                "open":        float(row.open) if row.open is not None else None,
                "high":        float(row.high) if row.high is not None else None,
                "low":         float(row.low) if row.low is not None else None,
                "close":       float(row.close) if row.close is not None else None,
                "volume":      row.volume,
                "dividends":   float(row.dividends) if row.dividends is not None else None,
                "stock_splits": float(row.stock_splits) if row.stock_splits is not None else None,
            }
            for row in ph_rows
        ],

        "dividend_history": [
            {
                "date":  row.date.isoformat() if row.date else None,
                "value": float(row.value) if row.value is not None else None,
            }
            for row in dh_rows
        ],

        # JSONB datasets — returned as-is
        "income_statement":            ds_map.get("income_statement"),
        "quarterly_income_statement":  ds_map.get("quarterly_income_statement"),
        "balance_sheet":               ds_map.get("balance_sheet"),
        "earnings_dates":              ds_map.get("earnings_dates"),
        "calendar":                    ds_map.get("calendar"),
        "earnings_estimate":           ds_map.get("earnings_estimate"),
        "revenue_estimate":            ds_map.get("revenue_estimate"),
        "eps_trend":                   ds_map.get("eps_trend"),
        "growth_estimates":            ds_map.get("growth_estimates"),
        "insider_purchases":           ds_map.get("insider_purchases"),
        "insider_transactions":        ds_map.get("insider_transactions"),

        "news": [
            {
                "news_id":      row.news_id,
                "title":        row.title,
                "publisher":    row.publisher,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "url":          row.url,
                "summary":      row.summary,
            }
            for row in news_rows
        ],

        "recommendations": [
            {
                "period":      row.period,
                "strong_buy":  row.strong_buy,
                "buy":         row.buy,
                "hold":        row.hold,
                "sell":        row.sell,
                "strong_sell": row.strong_sell,
            }
            for row in rec_rows
        ],

        "price_targets": {
            "current": float(pt_row.current) if pt_row and pt_row.current is not None else None,
            "low":     float(pt_row.low)     if pt_row and pt_row.low is not None else None,
            "high":    float(pt_row.high)    if pt_row and pt_row.high is not None else None,
            "mean":    float(pt_row.mean)    if pt_row and pt_row.mean is not None else None,
            "median":  float(pt_row.median)  if pt_row and pt_row.median is not None else None,
        } if pt_row else None,
    }
