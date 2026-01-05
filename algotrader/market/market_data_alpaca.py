from __future__ import annotations

import os
from typing import List, Optional

import requests

from .market_data_client import Bar, MarketDataClient


class AlpacaMarketDataClient(MarketDataClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 10.0,
        feed: str = "iex",
    ) -> None:
        self._api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self._api_secret = api_secret or os.getenv("ALPACA_SECRET_KEY", "") or os.getenv("ALPACA_API_SECRET", "")
        self._base_url = (base_url or os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")).rstrip("/")
        self._timeout = float(timeout_seconds)
        self._feed = str(feed).strip()

        if not self._api_key or not self._api_secret:
            raise ValueError("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY")

    def get_latest_price(self, symbol: str) -> float:
        url = f"{self._base_url}/v2/stocks/{symbol}/trades/latest"
        data = self._get(url, params={"feed": self._feed})
        return float(data["trade"]["p"])

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
    ) -> List[Bar]:
        url = f"{self._base_url}/v2/stocks/{symbol}/bars"
        params = {"timeframe": timeframe, "limit": int(limit), "feed": self._feed}
        if start_iso:
            params["start"] = start_iso
        if end_iso:
            params["end"] = end_iso

        data = self._get(url, params=params)
        bars: List[Bar] = []
        for b in data.get("bars", []):
            bars.append(
                Bar(
                    ts=b["t"],
                    open=float(b["o"]),
                    high=float(b["h"]),
                    low=float(b["l"]),
                    close=float(b["c"]),
                    volume=int(b["v"]),
                )
            )
        return bars

    def _get(self, url: str, params: dict) -> dict:
        headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
        }
        r = requests.get(url, headers=headers, params=params, timeout=self._timeout)
        if r.status_code == 403:
            raise requests.HTTPError(
                f"403 Forbidden from Alpaca Market Data. Check API keys and subscription/feed. url={r.url}",
                response=r,
            )
        r.raise_for_status()
        return r.json()
