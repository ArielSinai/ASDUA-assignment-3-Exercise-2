from __future__ import annotations

import time
import logging

from algotrader.agents.market_agent import MarketAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.agents.exec_agent import ExecAgent
from algotrader.execution.execution_stub import StubExecutionClient

from algotrader.data.market_data import StubMarketDataClient

from algotrader.core.cache import TTLCache
from algotrader.core.rate_limiter import RateLimiter
from algotrader.core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_PAPER,
    MAX_EXISTING_POSITION_PCT_TO_ADD,
)
from algotrader.execution.execution_alpaca import AlpacaExecutionClient

from algotrader.market.market_data_alpaca import AlpacaMarketDataClient
from algotrader.market.market_data_wrapped import CachedRateLimitedMarketDataClient
from algotrader.market.market_data_adapter import BarsToPricesAdapter


LOG = logging.getLogger("algotrader")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    symbols = ["PLTR", "NFLX", "PLTK"]

    use_real = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    if use_real:
        md_inner = AlpacaMarketDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_SECRET_KEY)
        cache = TTLCache()
        rl = RateLimiter(per_second=3, per_hour=300, per_day=2000)
        md_client = CachedRateLimitedMarketDataClient(inner=md_inner, cache=cache, rate_limiter=rl)
        md = BarsToPricesAdapter(md_client, timeframe="1Min")
    else:
        md = StubMarketDataClient(
            {
                "PLTR": list(range(1, 51)),
                "NFLX": list(range(50, 0, -1)),
                "PLTK": [100, 100, 100, 100, 100],
            }
        )

    market_agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)
    risk_agent = RiskAgent(max_position_pct=0.25)

    if use_real:
        execution_client = AlpacaExecutionClient(
            api_key=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            paper=ALPACA_PAPER,
        )
    else:
        execution_client = StubExecutionClient(starting_cash=100_000.0)

    LOG.info("Execution client: %s", type(execution_client).__name__)
    LOG.info("Market data: %s", type(md).__name__)

    exec_agent = ExecAgent(execution=execution_client, risk=risk_agent)

    trade_value_usd = 1000.0
    max_existing_position_pct_to_add = float(MAX_EXISTING_POSITION_PCT_TO_ADD)

    LOG.info("Starting agent_trader loop. Ctrl+C to exit.")
    while True:
        for sym in symbols:
            signal = market_agent.analyze(sym)
            LOG.info("Signal: %s", signal)

            portfolio = execution_client.get_portfolio()
            pos = execution_client.get_position(sym)

            position_value = 0.0
            if pos is not None and pos.qty > 0:
                position_value = float(pos.qty) * float(pos.avg_entry_price)

            equity = float(portfolio.equity) if portfolio.equity else 0.0
            position_pct = (position_value / equity) if equity > 0 else 1.0

            if (
                signal.action == "BUY"
                and pos is not None
                and pos.qty > 0
                and position_pct >= max_existing_position_pct_to_add
            ):
                LOG.info(
                    "Exec: %s",
                    f"Skipped BUY (position_pct={position_pct:.3f} >= {max_existing_position_pct_to_add:.3f})",
                )
            else:
                result = exec_agent.act(signal, trade_value=trade_value_usd)
                LOG.info("Exec: %s", result)

            portfolio = execution_client.get_portfolio()
            LOG.info(
                "Portfolio: cash=%.2f equity=%.2f positions=%s",
                portfolio.cash,
                portfolio.equity,
                {k: (v.qty, v.avg_entry_price) for k, v in portfolio.positions.items()},
            )

        time.sleep(2)


if __name__ == "__main__":
    main()
