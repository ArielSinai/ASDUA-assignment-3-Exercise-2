from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class NewsItem:
    symbol: str
    published_at: datetime
    title: str
    sentiment: float


class NewsDataClient(Protocol):
    def get_recent_news(
        self,
        symbol: str,
        *,
        as_of: datetime,
        lookback_days: int = 7,
        limit: int = 10,
    ) -> List[NewsItem]:
        ...


class StubNewsDataClient(NewsDataClient):
    """In-memory stub for unit tests/dev time (no real API calls)."""

    def __init__(self, items_by_symbol: Optional[Dict[str, Sequence[NewsItem]]] = None) -> None:
        self._items_by_symbol: Dict[str, List[NewsItem]] = {
            k: list(v) for k, v in (items_by_symbol or {}).items()
        }

    def get_recent_news(
        self,
        symbol: str,
        *,
        as_of: datetime,
        lookback_days: int = 7,
        limit: int = 10,
    ) -> List[NewsItem]:
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        start = as_of - timedelta(days=int(lookback_days))
        items = self._items_by_symbol.get(symbol, [])

        filtered = [
            x
            for x in items
            if (x.published_at.tzinfo is not None) and (start <= x.published_at <= as_of)
        ]

        filtered.sort(key=lambda x: x.published_at, reverse=True)
        return filtered[: int(limit)]
