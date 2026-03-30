"""
Serialization helpers: convert yfinance/pandas/numpy outputs
into JSON-safe Python types suitable for DB storage and API responses.
"""
from __future__ import annotations

import math
from datetime import datetime, date
from typing import Any

import numpy as np
import pandas as pd


def safe_value(v: Any) -> Any:
    """Recursively convert a value to a JSON-safe Python primitive."""
    if v is None:
        return None

    # numpy integers / floats
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.ndarray):
        return [safe_value(x) for x in v.tolist()]

    # pandas Timestamp / NaT
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.isoformat()
    if isinstance(v, pd.NaT.__class__):
        return None

    # Python float NaN / inf
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v

    # Python datetime / date
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()

    # Containers — recurse
    if isinstance(v, dict):
        return {str(k): safe_value(vv) for k, vv in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe_value(x) for x in v]

    return v


def dataframe_to_records(df: pd.DataFrame | None) -> list[dict] | None:
    """Convert a DataFrame to a list of row-dicts (index reset, values safe)."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    df = df.reset_index()
    records = [
        {str(col): safe_value(val) for col, val in row.items()}
        for _, row in df.iterrows()
    ]
    return records or None


def dataframe_to_column_dict(df: pd.DataFrame | None) -> dict | None:
    """
    Convert a DataFrame to a column-oriented dict:
      { column_name: { str(index): value, ... }, ... }
    Useful for financial statements where columns are dates.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    df = df.reset_index()
    result = {
        str(col): {str(i): safe_value(v) for i, v in enumerate(df[col])}
        for col in df.columns
    }
    return result or None


def series_to_records(s: pd.Series | None) -> list[dict] | None:
    """Convert a Series to a list of {date, value} dicts."""
    if s is None or not isinstance(s, pd.Series) or s.empty:
        return None
    records = [{"date": safe_value(idx), "value": safe_value(val)} for idx, val in s.items()]
    return records or None


def normalize_calendar(calendar: Any) -> dict | None:
    """
    yfinance calendar is a dict whose values may be Timestamps or lists of Timestamps.
    """
    if calendar is None:
        return None
    if isinstance(calendar, pd.DataFrame):
        return dataframe_to_column_dict(calendar)
    if isinstance(calendar, dict):
        return {str(k): safe_value(v) for k, v in calendar.items()}
    return None


def normalize_price_targets(pt: Any) -> dict | None:
    """
    get_analyst_price_targets() can return a dict, Series, or single-row DataFrame.
    We want: {current, low, high, mean, median}.
    """
    if pt is None:
        return None
    if isinstance(pt, pd.DataFrame):
        if pt.empty:
            return None
        row = pt.reset_index().iloc[0]
        return {str(k): safe_value(v) for k, v in row.items()}
    if isinstance(pt, pd.Series):
        return {str(k): safe_value(v) for k, v in pt.items()}
    if isinstance(pt, dict):
        return {str(k): safe_value(v) for k, v in pt.items()}
    return None


def normalize_news(news: Any) -> list[dict] | None:
    """
    yfinance news is a list of dicts.
    Handles both the legacy format and the newer nested-content format.
    """
    if not news:
        return None

    result = []
    for item in news:
        if not isinstance(item, dict):
            continue

        content = item.get("content") or {}
        if isinstance(content, dict) and content:
            # Newer yfinance format (>=0.2.37)
            title = content.get("title") or item.get("title")
            provider = content.get("provider") or {}
            publisher = (provider.get("displayName") if isinstance(provider, dict) else None) or item.get("publisher")
            canonical = content.get("canonicalUrl") or {}
            url = (canonical.get("url") if isinstance(canonical, dict) else None) or item.get("link")
            summary = content.get("summary") or item.get("summary")
            pub_time = content.get("pubDate") or content.get("publishedAt") or item.get("providerPublishTime")
        else:
            title = item.get("title")
            publisher = item.get("publisher")
            url = item.get("link")
            summary = item.get("summary")
            pub_time = item.get("providerPublishTime")

        # Convert unix timestamp → ISO string
        if isinstance(pub_time, (int, float)):
            from datetime import timezone
            pub_time = datetime.fromtimestamp(pub_time, tz=timezone.utc).isoformat()
        else:
            pub_time = safe_value(pub_time)

        result.append({
            "news_id": item.get("id") or item.get("uuid"),
            "title": title,
            "publisher": publisher,
            "published_at": pub_time,
            "url": url,
            "summary": summary,
            "raw_json": {str(k): safe_value(v) for k, v in item.items()},
        })

    return result or None
