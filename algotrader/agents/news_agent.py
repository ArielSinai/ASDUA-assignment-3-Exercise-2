from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from algotrader.agents.market_agent import MarketSignal
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
        *,
        strong_threshold: float = 0.60,
        min_confidence_for_signal: float = 0.60,
    ) -> None:
        self._news = news_data
        self.lookback_days = int(lookback_days)
        self.limit = int(limit)
        self.strong_threshold = float(strong_threshold)
        self.min_confidence_for_signal = float(min_confidence_for_signal)

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

    def generate_signal(self, symbol: str, *, as_of: Optional[datetime] = None) -> MarketSignal:
        insight = self.analyze(symbol, as_of=as_of)

        if insight.confidence < self.min_confidence_for_signal:
            return MarketSignal(
                symbol=symbol,
                action="HOLD",
                confidence=float(insight.confidence),
                reason=insight.reason,
            )

        if insight.sentiment >= self.strong_threshold:
            return MarketSignal(
                symbol=symbol,
                action="BUY",
                confidence=max(0.0, min(1.0, float(insight.confidence))),
                reason=f"Strong bullish news (sent={insight.sentiment:.2f}, conf={insight.confidence:.2f})",
            )

        if insight.sentiment <= -self.strong_threshold:
            return MarketSignal(
                symbol=symbol,
                action="SELL",
                confidence=max(0.0, min(1.0, float(insight.confidence))),
                reason=f"Strong bearish news (sent={insight.sentiment:.2f}, conf={insight.confidence:.2f})",
            )

        return MarketSignal(
            symbol=symbol,
            action="HOLD",
            confidence=max(0.0, min(1.0, float(insight.confidence))),
            reason=f"News not strong enough (sent={insight.sentiment:.2f}, conf={insight.confidence:.2f})",
        )
