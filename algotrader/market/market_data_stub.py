from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from .market_data_client import Bar, MarketDataClient


class StubMarketDataClient(MarketDataClient):
    """
    Dev-time stub:
    - If csv_path is provided, reads bars from CSV
    - Otherwise uses fixed prices
    """

    def __init__(
        self,
        fixed_prices: Optional[Dict[str, float]] = None,
        csv_path: Optional[str] = None,
    ) -> None:
        self._fixed_prices = fixed_prices or {"PLTR": 20.0, "NFLX": 500.0, "PLTK": 10.0}
        self._csv_path = Path(csv_path) if csv_path else None
        self._bars_cache: Dict[str, List[Bar]] = {}

    def get_latest_price(self, symbol: str) -> float:
        return float(self._fixed_prices[symbol])

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
    ) -> List[Bar]:
        if self._csv_path is None:
            price = self.get_latest_price(symbol)
            bars = [
                Bar(ts=f"stub-{i}", open=price, high=price, low=price, close=price, volume=1000)
                for i in range(limit)
            ]
            return bars

        if symbol not in self._bars_cache:
            self._bars_cache[symbol] = self._read_csv(symbol)

        return self._bars_cache[symbol][:limit]

    def _read_csv(self, symbol: str) -> List[Bar]:
        bars: List[Bar] = []
        with self._csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("symbol") != symbol:
                    continue
                bars.append(
                    Bar(
                        ts=row["ts"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                    )
                )
        return bars
