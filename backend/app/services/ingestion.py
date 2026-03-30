"""
Ingestion service: fetch raw data from yfinance and normalize it
into JSON-safe dicts ready for DB storage and API responses.
"""
from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

from app.utils.serializers import (
    dataframe_to_records,
    dataframe_to_column_dict,
    series_to_records,
    safe_value,
    normalize_calendar,
    normalize_price_targets,
    normalize_news,
)

logger = logging.getLogger(__name__)

# Datasets that are DataFrames stored as column-oriented dicts
_COLUMN_DICT_DATASETS = {
    "income_statement",
    "quarterly_income_statement",
    "balance_sheet",
    "earnings_estimate",
    "revenue_estimate",
    "eps_trend",
    "growth_estimates",
}

# Datasets that are DataFrames stored as list-of-row dicts
_RECORDS_DATASETS = {
    "earnings_dates",
    "insider_purchases",
    "insider_transactions",
    "recommendations",
}


def _try(symbol: str, name: str, fn):
    """Execute fn(), log and return None on any error."""
    try:
        return fn()
    except Exception as exc:
        logger.warning("[%s] %s failed: %s", symbol, name, exc)
        return None


def fetch_raw(symbol: str) -> dict[str, Any]:
    """Fetch all datasets from yfinance. Each dataset is the raw yfinance object."""
    t = yf.Ticker(symbol)

    raw: dict[str, Any] = {
        "info":                      _try(symbol, "info",                      lambda: t.info or {}),
        "price_history":             _try(symbol, "price_history",             lambda: t.history(period="7d", interval="1m")),
        "dividend_history":          _try(symbol, "dividend_history",          lambda: t.dividends),
        "income_statement":          _try(symbol, "income_statement",          lambda: t.income_stmt),
        "quarterly_income_statement":_try(symbol, "quarterly_income_statement",lambda: t.quarterly_income_stmt),
        "balance_sheet":             _try(symbol, "balance_sheet",             lambda: t.get_balance_sheet(as_dict=False, pretty=False, freq="quarterly")),
        "earnings_dates":            _try(symbol, "earnings_dates",            lambda: t.earnings_dates),
        "calendar":                  _try(symbol, "calendar",                  lambda: t.calendar),
        "recommendations":           _try(symbol, "recommendations",           lambda: t.get_recommendations()),
        "price_targets":             _try(symbol, "price_targets",             lambda: t.get_analyst_price_targets()),
        "earnings_estimate":         _try(symbol, "earnings_estimate",         lambda: t.earnings_estimate),
        "revenue_estimate":          _try(symbol, "revenue_estimate",          lambda: t.revenue_estimate),
        "eps_trend":                 _try(symbol, "eps_trend",                 lambda: t.eps_trend),
        "growth_estimates":          _try(symbol, "growth_estimates",          lambda: t.growth_estimates),
        "insider_purchases":         _try(symbol, "insider_purchases",         lambda: t.insider_purchases),
        "insider_transactions":      _try(symbol, "insider_transactions",      lambda: t.insider_transactions),
        "news":                      _try(symbol, "news",                      lambda: t.news),
    }

    return raw


def normalize(symbol: str, raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert raw yfinance output into JSON-safe dicts.
    Returns a flat dict with all fields ready for DB writes and API responses.
    """
    info: dict = raw.get("info") or {}

    return {
        "symbol": symbol.upper(),
        "company_name": info.get("longName") or info.get("shortName"),

        # ── Scalar metrics ──────────────────────────────────────────
        "pe":           safe_value(info.get("forwardPE")),
        "dividend_yield": safe_value(info.get("dividendRate")),
        "market_cap":   safe_value(info.get("marketCap")),
        "volume":       safe_value(info.get("volume")),
        "volume_avg":   safe_value(info.get("averageVolume")),
        "volume_avg_10": safe_value(info.get("averageVolume10days")),

        # ── Timeseries ──────────────────────────────────────────────
        "price_history":    dataframe_to_records(raw.get("price_history")),
        "dividend_history": series_to_records(raw.get("dividend_history")),

        # ── Financial statements (column-oriented) ──────────────────
        "income_statement":           dataframe_to_column_dict(raw.get("income_statement")),
        "quarterly_income_statement": dataframe_to_column_dict(raw.get("quarterly_income_statement")),
        "balance_sheet":              dataframe_to_column_dict(raw.get("balance_sheet")),
        "earnings_estimate":          dataframe_to_column_dict(raw.get("earnings_estimate")),
        "revenue_estimate":           dataframe_to_column_dict(raw.get("revenue_estimate")),
        "eps_trend":                  dataframe_to_column_dict(raw.get("eps_trend")),
        "growth_estimates":           dataframe_to_column_dict(raw.get("growth_estimates")),

        # ── Row-oriented datasets ───────────────────────────────────
        "earnings_dates":        dataframe_to_records(raw.get("earnings_dates")),
        "insider_purchases":     dataframe_to_records(raw.get("insider_purchases")),
        "insider_transactions":  dataframe_to_records(raw.get("insider_transactions")),
        "recommendations":       dataframe_to_records(raw.get("recommendations")),

        # ── Special cases ───────────────────────────────────────────
        "calendar":      normalize_calendar(raw.get("calendar")),
        "price_targets": normalize_price_targets(raw.get("price_targets")),
        "news":          normalize_news(raw.get("news")),
    }
