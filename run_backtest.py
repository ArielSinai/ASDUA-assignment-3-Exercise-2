#!/usr/bin/env python3
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from algotrader.agents.market_agent import MarketAgent
from algotrader.agents.news_agent import NewsAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.agents.exec_agent import ExecAgent
from algotrader.backtest.backtest_market_data import BacktestMarketData
from algotrader.backtest.backtest_execution import BacktestExecutionClient
from algotrader.backtest.alpaca_history import fetch_prices_by_symbol, make_week_window_utc, BacktestWindow
from algotrader.core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    BACKTEST_START,
    BACKTEST_END,
    BACKTEST_TIMEFRAME,
)
from algotrader.crew.crew_runner import CrewRunner
from algotrader.data.news_data import StubNewsDataClient, NewsItem
from algotrader.market.market_data_alpaca import AlpacaMarketDataClient
from algotrader.market.market_data_wrapped_adapter import BarsToPricesAdapter


LOG = logging.getLogger("backtest")


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _parse_iso_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def compute_metrics(equity_curve: List[float]) -> dict:
    if not equity_curve:
        return {"return_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0}

    start = float(equity_curve[0])
    end = float(equity_curve[-1])
    return_pct = 0.0 if start == 0 else ((end - start) / start) * 100.0

    peak = float(equity_curve[0])
    max_dd = 0.0
    for v in equity_curve:
        v = float(v)
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    returns = []
    for i in range(1, len(equity_curve)):
        r = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] if equity_curve[i-1] > 0 else 0.0
        returns.append(r)
    
    avg_return = sum(returns) / len(returns) if returns else 0.0
    std_return = (sum((r - avg_return)**2 for r in returns) / len(returns))**0.5 if returns else 1.0
    sharpe = (avg_return / std_return) * (252**0.5) if std_return > 0 else 0.0

    return {
        "return_pct": float(return_pct),
        "max_drawdown_pct": float(max_dd * 100.0),
        "sharpe_ratio": float(sharpe),
    }


def run_backtest(
    *,
    prices_by_symbol: Dict[str, List[float]],
    symbols: List[str],
    starting_cash: float = 100_000.0,
    trade_value_usd: float = 10_000.0,
    use_crew: bool = True,
) -> dict:
    md = BacktestMarketData(prices_by_symbol)
    ex = BacktestExecutionClient(md, starting_cash=starting_cash)
    
    market_agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)
    risk_agent = RiskAgent(max_position_pct=0.25)
    exec_agent = ExecAgent(execution=ex, risk=risk_agent)
    
    as_of = datetime.now(timezone.utc)
    stub_news = {
        "PLTR": [NewsItem("PLTR", as_of - timedelta(days=1), "Positive news", 0.3)],
        "NFLX": [NewsItem("NFLX", as_of - timedelta(days=1), "Neutral news", 0.0)],
        "PLTK": [NewsItem("PLTK", as_of - timedelta(days=1), "Negative news", -0.2)],
    }
    news_client = StubNewsDataClient(stub_news)
    news_agent = NewsAgent(news_client, lookback_days=7, limit=10)
    
    crew_runner = None
    if use_crew:
        crew_runner = CrewRunner(
            market_agent=market_agent,
            news_agent=news_agent,
            risk_agent=risk_agent,
            score_hold_threshold=0.15,
        )

    steps = md.max_steps()
    start_equity = float(ex.get_portfolio().equity)
    equity_curve = [start_equity]
    trades = 0

    LOG.info(f"Starting backtest: {steps} steps, starting equity=${start_equity:.2f}")

    for i in range(steps):
        md.set_index(i)

        for sym in symbols:
            pos = ex.get_position(sym)
            portfolio = ex.get_portfolio()
            
            if use_crew and crew_runner:
                position_value = 0.0 if pos is None else float(pos.qty) * float(pos.avg_entry_price)
                decision = crew_runner.decide(
                    sym,
                    equity=float(portfolio.equity),
                    existing_position_value=position_value,
                    default_trade_value_usd=trade_value_usd,
                    as_of=as_of,
                )
                signal = decision.signal
                trade_val = decision.approved_trade_value if signal.action == "BUY" else trade_value_usd
            else:
                signal = market_agent.analyze(sym)
                trade_val = trade_value_usd

            if signal.action == "BUY" and pos is not None and pos.qty > 0:
                continue
            if signal.action == "SELL" and (pos is None or pos.qty <= 0):
                continue
            if signal.action == "HOLD":
                continue

            res = exec_agent.act(signal, trade_value=float(trade_val))
            if res.executed:
                trades += 1
                LOG.debug(f"Step {i}: {sym} {signal.action} executed")

        equity_curve.append(float(ex.get_portfolio().equity))

    end_equity = float(ex.get_portfolio().equity)
    metrics = compute_metrics(equity_curve)

    LOG.info(f"Backtest complete: end equity=${end_equity:.2f}, trades={trades}")

    return {
        "start_equity": start_equity,
        "end_equity": end_equity,
        "trades_executed": trades,
        "equity_curve": equity_curve,
        "metrics": metrics,
    }


def main() -> None:
    _setup_logging()
    
    symbols = ["PLTR", "NFLX", "PLTK"]
    use_alpaca = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    LOG.info("=" * 60)
    LOG.info("BACKTEST MODE")
    LOG.info("=" * 60)

    if use_alpaca:
        LOG.info("Using Alpaca historical data")
        md = AlpacaMarketDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_SECRET_KEY)

        if BACKTEST_START and BACKTEST_END:
            window = BacktestWindow(start=_parse_iso_dt(BACKTEST_START), end=_parse_iso_dt(BACKTEST_END))
            source = f"Alpaca ({BACKTEST_START} to {BACKTEST_END}, {BACKTEST_TIMEFRAME})"
        else:
            window = make_week_window_utc(days=7)
            source = f"Alpaca (last 7 days, {BACKTEST_TIMEFRAME})"

        LOG.info(f"Fetching prices: {source}")
        prices = fetch_prices_by_symbol(
            md=md,
            symbols=symbols,
            window=window,
            timeframe=BACKTEST_TIMEFRAME,
            limit=1000,
        )
    else:
        LOG.info("Using stub data (no Alpaca keys)")
        prices = {
            "PLTR": [20.0 + i * 0.1 for i in range(100)],
            "NFLX": [500.0 + i * 0.5 for i in range(100)],
            "PLTK": [10.0 + i * 0.05 for i in range(100)],
        }
        source = "Stub sample data"

    LOG.info(f"Running backtest with crew integration")
    result = run_backtest(
        prices_by_symbol=prices,
        symbols=symbols,
        starting_cash=100_000.0,
        trade_value_usd=10_000.0,
        use_crew=True,
    )

    LOG.info("=" * 60)
    LOG.info("BACKTEST RESULTS")
    LOG.info("=" * 60)
    LOG.info(f"Source:           {source}")
    LOG.info(f"Start Equity:     ${result['start_equity']:,.2f}")
    LOG.info(f"End Equity:       ${result['end_equity']:,.2f}")
    LOG.info(f"Return:           {result['metrics']['return_pct']:.2f}%")
    LOG.info(f"Max Drawdown:     {result['metrics']['max_drawdown_pct']:.2f}%")
    LOG.info(f"Sharpe Ratio:     {result['metrics']['sharpe_ratio']:.2f}")
    LOG.info(f"Trades Executed:  {result['trades_executed']}")
    LOG.info(f"Equity Samples:   {len(result['equity_curve'])}")
    LOG.info("=" * 60)


if __name__ == "__main__":
    main()