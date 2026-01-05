from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from algotrader.data.news_data import NewsDataClient, NewsItem


@dataclass(frozen=True)
class NewsInsight:
    symbol: str
    sentiment: float
    confidence: float
    headlines: List[str]
    reason: str


class NewsAgent:
    def __init__(
        self,
        news_data: NewsDataClient,
        lookback_days: int = 7,
        limit: int = 10,
    ) -> None:
        self._news = news_data
        self.lookback_days = int(lookback_days)
        self.limit = int(limit)

    def analyze(self, symbol: str, *, as_of: Optional[datetime] = None) -> NewsInsight:
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        items: List[NewsItem] = self._news.get_recent_news(
            symbol,
            as_of=as_of,
            lookback_days=self.lookback_days,
            limit=self.limit,
        )

        if not items:
            return NewsInsight(
                symbol=symbol,
                sentiment=0.0,
                confidence=0.0,
                headlines=[],
                reason="No recent news",
            )

        sentiments = [float(x.sentiment) for x in items]
        avg = sum(sentiments) / len(sentiments)

        confidence = min(1.0, len(items) / 5.0)
        headlines = [x.title for x in items[:5]]

        reason = f"Avg sentiment={avg:.3f} from {len(items)} items (lookback_days={self.lookback_days})"
        return NewsInsight(
            symbol=symbol,
            sentiment=float(avg),
            confidence=float(confidence),
            headlines=headlines,
            reason=reason,
        )
