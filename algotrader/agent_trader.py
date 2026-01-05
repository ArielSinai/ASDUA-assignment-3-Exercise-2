from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta

from algotrader.agents.exec_agent import ExecAgent, ExecResult
from algotrader.agents.market_agent import MarketAgent, MarketSignal
from algotrader.agents.news_agent import NewsAgent
from algotrader.agents.risk_agent import RiskAgent
from algotrader.core.cache import TTLCache
from algotrader.core.config import (
    ALPACA_API_KEY,
    ALPACA_PAPER,
    ALPACA_SECRET_KEY,
    COOLDOWN_SECONDS,
    MAX_EXISTING_POSITION_PCT_TO_ADD,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    USE_REAL_NEWS,
    NEWS_CACHE_TTL_SECONDS,
    NEWS_LOOKBACK_DAYS,
    NEWS_LIMIT,
)
from algotrader.core.rate_limiter import RateLimiter
from algotrader.data.news_data import NewsItem, StubNewsDataClient
from algotrader.data.news_data_alpaca import AlpacaNewsDataClient
from algotrader.data.news_data_wrapped import CachedRateLimitedNewsDataClient
from algotrader.execution.execution_alpaca import AlpacaExecutionClient
from algotrader.execution.execution_stub import StubExecutionClient
from algotrader.market.market_data_alpaca import AlpacaMarketDataClient
from algotrader.market.market_data_stub import StubMarketDataClient as BarsStubMarketDataClient
from algotrader.market.market_data_wrapped import CachedRateLimitedMarketDataClient
from algotrader.market.market_data_wrapped_adapter import BarsToPricesAdapter

LOG = logging.getLogger("algotrader")


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _summarize_positions(portfolio) -> dict:
    out = {}
    for sym, p in portfolio.positions.items():
        out[sym] = (float(p.qty), float(p.avg_entry_price))
    return out


def _position_value_pct(*, equity: float, position_value: float) -> float:
    if equity <= 0:
        return 0.0
    return float(position_value) / float(equity)


def _maybe_make_tpsl_signal(
    *,
    symbol: str,
    position,
    latest_price: float,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> MarketSignal | None:
    if position is None or position.qty <= 0:
        return None

    entry = float(position.avg_entry_price)
    if entry <= 0:
        return None

    pnl_pct = (float(latest_price) - entry) / entry

    if pnl_pct >= float(take_profit_pct) or pnl_pct <= -float(stop_loss_pct):
        return MarketSignal(
            symbol=symbol,
            action="SELL",
            confidence=1.0,
            reason=f"TP/SL triggered (pnl_pct={pnl_pct:.3f})",
        )

    return None


def _combine_market_and_news(market: MarketSignal, news_sentiment: float, news_confidence: float) -> MarketSignal:
    if market.action == "HOLD":
        return market

    if news_confidence < 0.4:
        return market

    bearish = news_sentiment <= -0.25
    bullish = news_sentiment >= 0.25

    if market.action == "BUY" and bearish:
        return MarketSignal(
            symbol=market.symbol,
            action="HOLD",
            confidence=max(0.0, market.confidence - 0.3),
            reason=f"Market said BUY but news bearish (sent={news_sentiment:.2f})",
        )

    if market.action == "SELL" and bullish:
        return MarketSignal(
            symbol=market.symbol,
            action="HOLD",
            confidence=max(0.0, market.confidence - 0.3),
            reason=f"Market said SELL but news bullish (sent={news_sentiment:.2f})",
        )

    return market


def main() -> None:
    _setup_logging()

    symbols = ["PLTR", "NFLX", "PLTK"]
    use_real_exec = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    cache = TTLCache()
    rl = RateLimiter(per_second=3, per_hour=300, per_day=5000)

    if use_real_exec:
        bars_md = AlpacaMarketDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_SECRET_KEY)
        exec_client = AlpacaExecutionClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY, paper=ALPACA_PAPER)
    else:
        bars_md = BarsStubMarketDataClient()
        exec_client = StubExecutionClient(starting_cash=100_000.0)

    cached_bars_md = CachedRateLimitedMarketDataClient(
        inner=bars_md,
        cache=cache,
        rate_limiter=rl,
        cache_ttl_seconds_latest_price=2.0,
        cache_ttl_seconds_bars=60.0,
        limiter_key_prefix="marketdata",
    )

    md = BarsToPricesAdapter(cached_bars_md, timeframe="1Min", limit=60)

    as_of = datetime.now(timezone.utc)
    stub_news_items = {
        "PLTR": [
            NewsItem("PLTR", as_of - timedelta(days=1), "Stub: PLTR positive", 0.4),
            NewsItem("PLTR", as_of - timedelta(days=2), "Stub: PLTR positive", 0.3),
        ],
        "NFLX": [
            NewsItem("NFLX", as_of - timedelta(days=1), "Stub: NFLX negative", -0.3),
            NewsItem("NFLX", as_of - timedelta(days=3), "Stub: NFLX negative", -0.1),
        ],
        "PLTK": [
            NewsItem("PLTK", as_of - timedelta(days=2), "Stub: PLTK neutral", 0.0),
        ],
    }

    if USE_REAL_NEWS:
        try:
            news_inner = AlpacaNewsDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_SECRET_KEY)
            LOG.info("News data: AlpacaNewsDataClient")
        except Exception as e:
            LOG.warning("Real news disabled (fallback to stub). reason=%s", e)
            news_inner = StubNewsDataClient(stub_news_items)
            LOG.info("News data: StubNewsDataClient")
    else:
        news_inner = StubNewsDataClient(stub_news_items)
        LOG.info("News data: StubNewsDataClient")

    news_client = CachedRateLimitedNewsDataClient(
        inner=news_inner,
        cache=cache,
        rate_limiter=rl,
        cache_ttl_seconds=float(NEWS_CACHE_TTL_SECONDS),
        limiter_key_prefix="news",
    )

    market_agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)
    news_agent = NewsAgent(news_client, lookback_days=int(NEWS_LOOKBACK_DAYS), limit=int(NEWS_LIMIT))
    risk_agent = RiskAgent(max_position_pct=0.25)
    exec_agent = ExecAgent(execution=exec_client, risk=risk_agent)

    cooldowns: dict[str, float] = {}
    trade_value_usd = 1000.0

    LOG.info("Execution client: %s", type(exec_client).__name__)
    LOG.info("Market data: %s", type(md).__name__)
    LOG.info("Starting agent_trader loop. Ctrl+C to exit.")

    while True:
        for sym in symbols:
            now_ts = time.time()
            until = cooldowns.get(sym, 0.0)
            if now_ts < until:
                LOG.info("Exec: Skipped %s (cooldown %.1fs remaining)", sym, until - now_ts)
                continue

            portfolio = exec_client.get_portfolio()
            pos = exec_client.get_position(sym)

            latest_price = float(md.get_last_price(sym))
            tpsl = _maybe_make_tpsl_signal(
                symbol=sym,
                position=pos,
                latest_price=latest_price,
                take_profit_pct=float(TAKE_PROFIT_PCT),
                stop_loss_pct=float(STOP_LOSS_PCT),
            )

            if tpsl is not None:
                signal = tpsl
            else:
                market_signal = market_agent.analyze(sym)
                insight = news_agent.analyze(sym)
                signal = _combine_market_and_news(market_signal, insight.sentiment, insight.confidence)

            if signal.action == "BUY":
                position_value = 0.0 if pos is None else float(pos.qty) * float(pos.avg_entry_price)
                pct = _position_value_pct(equity=float(portfolio.equity), position_value=position_value)
                if pos is not None and pos.qty > 0 and pct >= float(MAX_EXISTING_POSITION_PCT_TO_ADD):
                    LOG.info(
                        "Exec: Skipped BUY (%s position_pct=%.3f >= %.3f)",
                        sym,
                        pct,
                        float(MAX_EXISTING_POSITION_PCT_TO_ADD),
                    )
                    cooldowns[sym] = time.time() + float(COOLDOWN_SECONDS)
                    continue

            LOG.info("Signal: %s", signal)

            res: ExecResult = exec_agent.act(signal, trade_value=float(trade_value_usd))
            if res.executed:
                cooldowns[sym] = time.time() + float(COOLDOWN_SECONDS)
            LOG.info("Exec: %s", res)

            portfolio2 = exec_client.get_portfolio()
            LOG.info(
                "Portfolio: cash=%.2f equity=%.2f positions=%s",
                float(portfolio2.cash),
                float(portfolio2.equity),
                _summarize_positions(portfolio2),
            )

        time.sleep(2.0)


if __name__ == "__main__":
    main()
