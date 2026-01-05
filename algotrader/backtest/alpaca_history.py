from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from algotrader.market.market_data_client import Bar, MarketDataClient


@dataclass(frozen=True)
class BacktestWindow:
    start: datetime
    end: datetime

    def to_iso(self) -> tuple[str, str]:
        return (self.start.isoformat(), self.end.isoformat())


def make_week_window_utc(end: Optional[datetime] = None, days: int = 7) -> BacktestWindow:
    end_dt = end or datetime.now(timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    end_dt = end_dt.astimezone(timezone.utc)

    start_dt = end_dt - timedelta(days=int(days))
    return BacktestWindow(start=start_dt, end=end_dt)


def bars_to_close_prices(bars: Iterable[Bar]) -> List[float]:
    out: List[float] = []
    for b in bars:
        out.append(float(b.close))
    return out


def fetch_prices_by_symbol(
    *,
    md: MarketDataClient,
    symbols: Sequence[str],
    window: BacktestWindow,
    timeframe: str = "1Hour",
    limit: int = 1000,
) -> Dict[str, List[float]]:
    start_iso, end_iso = window.to_iso()
    prices_by_symbol: Dict[str, List[float]] = {}

    for sym in symbols:
        bars = md.get_bars(sym, timeframe=timeframe, limit=int(limit), start_iso=start_iso, end_iso=end_iso)
        prices_by_symbol[sym] = bars_to_close_prices(bars)

    return prices_by_symbol
