from __future__ import annotations

import time
import logging

from algotrader.agents.market_agent import MarketAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.agents.exec_agent import ExecAgent
from algotrader.execution.execution_stub import StubExecutionClient

from algotrader.data.market_data import StubMarketDataClient

from algotrader.core.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER
from algotrader.execution.execution_alpaca import AlpacaExecutionClient


LOG = logging.getLogger("algotrader")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    symbols = ["PLTR", "NFLX", "PLTK"]

    md = StubMarketDataClient(
        {
            "PLTR": list(range(1, 51)),
            "NFLX": list(range(50, 0, -1)),
            "PLTK": [100, 100, 100, 100, 100],
        }
    )

    market_agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)
    risk_agent = RiskAgent(max_position_pct=0.25)

    use_real_exec = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    if use_real_exec:
        execution_client = AlpacaExecutionClient(
            api_key=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            paper=ALPACA_PAPER,
        )
    else:
        execution_client = StubExecutionClient(starting_cash=100_000.0)

    LOG.info("Execution client: %s", type(execution_client).__name__)

    exec_agent = ExecAgent(execution=execution_client, risk=risk_agent)

    trade_value_usd = 1000.0

    LOG.info("Starting agent_trader loop. Ctrl+C to exit.")
    while True:
        for sym in symbols:
            signal = market_agent.analyze(sym)
            LOG.info("Signal: %s", signal)

            pos = execution_client.get_position(sym)
            if signal.action == "BUY" and pos is not None and pos.qty > 0:
                LOG.info("Exec: %s", "Skipped BUY (already holding position)")
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
