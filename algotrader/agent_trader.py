from __future__ import annotations

import time
import logging

from algotrader.agents.market_agent import MarketAgent, MarketSignal
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
    MIN_POSITION_PCT_TO_SELL,
    COOLDOWN_SECONDS,
    TAKE_PROFIT_PCT,
    STOP_LOSS_PCT,
)
from algotrader.core.logging_config import setup_logging

from algotrader.execution.execution_alpaca import AlpacaExecutionClient
from algotrader.market.market_data_alpaca import AlpacaMarketDataClient
from algotrader.market.market_data_wrapped import CachedRateLimitedMarketDataClient
from algotrader.market.market_data_adapter import BarsToPricesAdapter


def main() -> None:
    LOG = setup_logging(level=logging.INFO, log_file="algotrader.log")

    symbols = ["PLTR", "NFLX", "PLTK"]

    use_real = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    if use_real:
        md_inner = AlpacaMarketDataClient(
            api_key=ALPACA_API_KEY,
            api_secret=ALPACA_SECRET_KEY,
        )
        cache = TTLCache()
        rl = RateLimiter(per_second=3, per_hour=300, per_day=2000)
        md_client = CachedRateLimitedMarketDataClient(
            inner=md_inner,
            cache=cache,
            rate_limiter=rl,
        )
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
    cooldowns: dict[str, float] = {}

    LOG.info("Starting agent_trader loop. Ctrl+C to exit.")
    while True:
        for sym in symbols:
            now = time.time()
            until = cooldowns.get(sym, 0.0)
            if now < until:
                LOG.info(
                    "Exec: %s",
                    f"Skipped {sym} (cooldown {until - now:.1f}s remaining)",
                )
                continue

            signal = market_agent.analyze(sym)
            LOG.info("Signal: %s", signal)

            portfolio = execution_client.get_portfolio()
            pos = execution_client.get_position(sym)

            latest_price = None
            try:
                if hasattr(md, "get_latest_price"):
                    latest_price = float(md.get_latest_price(sym))
            except Exception:
                latest_price = None

            position_value = 0.0
            if pos is not None and pos.qty > 0:
                price = latest_price if latest_price and latest_price > 0 else pos.avg_entry_price
                position_value = float(pos.qty) * float(price)

            equity = float(portfolio.equity) if portfolio.equity else 0.0
            position_pct = (position_value / equity) if equity > 0 else 1.0

            force_sell = False
            if (
                pos is not None
                and pos.qty > 0
                and latest_price
                and latest_price > 0
                and pos.avg_entry_price > 0
            ):
                pnl_pct = (latest_price - pos.avg_entry_price) / pos.avg_entry_price
                if pnl_pct >= TAKE_PROFIT_PCT or pnl_pct <= -STOP_LOSS_PCT:
                    force_sell = True
                    signal = MarketSignal(
                        symbol=sym,
                        action="SELL",
                        confidence=1.0,
                        reason=f"TP/SL triggered (pnl_pct={pnl_pct:.3f})",
                    )
                    LOG.info("Signal override: %s", signal)

            if (
                signal.action == "BUY"
                and pos is not None
                and pos.qty > 0
                and position_pct >= MAX_EXISTING_POSITION_PCT_TO_ADD
            ):
                LOG.info(
                    "Exec: %s",
                    f"Skipped BUY (position_pct={position_pct:.3f} >= {MAX_EXISTING_POSITION_PCT_TO_ADD:.3f})",
                )
            elif signal.action == "SELL":
                if pos is None or pos.qty <= 0:
                    LOG.info("Exec: %s", "Skipped SELL (no position)")
                elif (not force_sell) and position_pct < MIN_POSITION_PCT_TO_SELL:
                    LOG.info(
                        "Exec: %s",
                        f"Skipped SELL (position_pct={position_pct:.3f} < {MIN_POSITION_PCT_TO_SELL:.3f})",
                    )
                else:
                    result = exec_agent.act(signal, trade_value=trade_value_usd)
                    LOG.info("Exec: %s", result)
                    if result.executed:
                        cooldowns[sym] = time.time() + COOLDOWN_SECONDS
            else:
                result = exec_agent.act(signal, trade_value=trade_value_usd)
                LOG.info("Exec: %s", result)
                if result.executed:
                    cooldowns[sym] = time.time() + COOLDOWN_SECONDS

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
