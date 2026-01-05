from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional

import os
import requests

from .news_data import NewsDataClient, NewsItem


class AlpacaNewsDataClient(NewsDataClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self._api_secret = api_secret or os.getenv("ALPACA_API_SECRET", "") or os.getenv("ALPACA_SECRET_KEY", "")
        self._base_url = (base_url or os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")).rstrip("/")
        self._timeout = float(timeout_seconds)

        if not self._api_key or not self._api_secret:
            raise ValueError("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY")

    def get_recent_news(
        self,
        symbol: str,
        *,
        as_of: datetime,
        lookback_days: int = 7,
        limit: int = 20,
    ) -> List[NewsItem]:
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        start = as_of - timedelta(days=int(lookback_days))
        url = f"{self._base_url}/v1beta1/news"

        params = {
            "symbols": symbol,
            "start": start.isoformat(),
            "end": as_of.isoformat(),
            "limit": int(limit),
            "sort": "desc",
        }

        data = self._get(url, params=params)

        raw_items = data.get("news", []) or data.get("items", []) or []
        out: List[NewsItem] = []

        for it in raw_items:
            created = it.get("created_at") or it.get("updated_at") or it.get("time") or it.get("timestamp")
            ts = _parse_dt(created) if created else as_of

            headline = it.get("headline") or it.get("title") or it.get("summary") or ""
            sent = _headline_sentiment(headline)

            out.append(NewsItem(symbol, ts, headline, sent))

        out.sort(key=_news_item_time, reverse=True)
        return out

    def _get(self, url: str, params: dict) -> dict:
        headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
        }
        r = requests.get(url, headers=headers, params=params, timeout=self._timeout)
        r.raise_for_status()
        return r.json()


def _parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _headline_sentiment(headline: str) -> float:
    h = (headline or "").lower()

    pos_words = [
        "beats", "beat", "surge", "soar", "record", "strong", "upgrade", "upgrades",
        "profit", "growth", "bullish", "wins", "win", "raises", "raise", "outperform",
        "buy rating", "partnership", "contract",
    ]
    neg_words = [
        "miss", "misses", "plunge", "drop", "falls", "fall", "weak", "downgrade",
        "downgrades", "loss", "lawsuit", "probe", "investigation", "bearish",
        "cuts", "cut", "warning", "slowdown",
    ]

    score = 0.0
    for w in pos_words:
        if w in h:
            score += 0.25
    for w in neg_words:
        if w in h:
            score -= 0.25

    if score > 1.0:
        score = 1.0
    if score < -1.0:
        score = -1.0
    return float(score)


def _news_item_time(item: NewsItem) -> float:
    for attr in ("as_of", "timestamp", "published_at", "created_at", "time", "dt", "date"):
        v = getattr(item, attr, None)
        if isinstance(v, datetime):
            return v.timestamp()
    return 0.0
