from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Literal, List


Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    action: Action
    confidence: float  # 0..1
    reason: str


class MarketDataClient(Protocol):
    """
    Interface (protocol) so we can inject a stub in tests and a real client later.
    """

    def get_last_price(self, symbol: str) -> float:
        ...

    def get_recent_prices(self, symbol: str, lookback: int) -> List[float]:
        """
        Returns a list of recent prices, ordered from oldest -> newest.
        """
        ...


class MarketAgent:
    """
    A simple, deterministic market agent:
    - Uses short/long moving averages on recent prices.
    - Produces BUY when short MA > long MA by a threshold
    - Produces SELL when short MA < long MA by a threshold
    - Otherwise HOLD
    """

    def __init__(
        self,
        market_data: MarketDataClient,
        short_window: int = 5,
        long_window: int = 20,
        threshold: float = 0.002,  # 0.2%
    ) -> None:
        if short_window <= 0 or long_window <= 0:
            raise ValueError("windows must be positive")
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        if threshold < 0:
            raise ValueError("threshold must be >= 0")

        self.market_data = market_data
        self.short_window = short_window
        self.long_window = long_window
        self.threshold = threshold

    def analyze(self, symbol: str) -> TradeSignal:
        prices = self.market_data.get_recent_prices(symbol, self.long_window)
        if len(prices) < self.long_window:
            return TradeSignal(
                symbol=symbol,
                action="HOLD",
                confidence=0.0,
                reason=f"Not enough data: need {self.long_window}, got {len(prices)}",
            )

        short_prices = prices[-self.short_window :]
        long_prices = prices[-self.long_window :]

        short_ma = sum(short_prices) / len(short_prices)
        long_ma = sum(long_prices) / len(long_prices)

        # Relative diff
        diff = (short_ma - long_ma) / long_ma

        if diff > self.threshold:
            confidence = min(1.0, diff / (self.threshold * 5) if self.threshold > 0 else 1.0)
            return TradeSignal(
                symbol=symbol,
                action="BUY",
                confidence=round(confidence, 3),
                reason=f"Short MA ({short_ma:.2f}) above long MA ({long_ma:.2f}) by {diff*100:.2f}%",
            )

        if diff < -self.threshold:
            confidence = min(1.0, (-diff) / (self.threshold * 5) if self.threshold > 0 else 1.0)
            return TradeSignal(
                symbol=symbol,
                action="SELL",
                confidence=round(confidence, 3),
                reason=f"Short MA ({short_ma:.2f}) below long MA ({long_ma:.2f}) by {abs(diff)*100:.2f}%",
            )

        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            confidence=0.3,
            reason=f"No strong trend: diff {diff*100:.2f}% within threshold",
        )
