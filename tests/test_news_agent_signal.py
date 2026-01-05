from datetime import datetime, timezone

from algotrader.agents.news_agent import NewsAgent
from algotrader.data.news_data import NewsItem, StubNewsDataClient


def test_news_agent_generates_buy_on_strong_bullish_news():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    stub = StubNewsDataClient(
        items_by_symbol={
            "PLTR": [
                NewsItem("PLTR", as_of, "Very bullish", 0.95),
                NewsItem("PLTR", as_of, "Bullish again", 0.80),
                NewsItem("PLTR", as_of, "More bullish", 0.90),
                NewsItem("PLTR", as_of, "Bullish story", 0.85),
                NewsItem("PLTR", as_of, "Strong tailwind", 0.75),
            ]
        }
    )

    agent = NewsAgent(stub, lookback_days=7, limit=10, strong_threshold=0.60, min_confidence_for_signal=0.60)
    sig = agent.generate_signal("PLTR", as_of=as_of)

    assert sig.action == "BUY"
    assert sig.confidence > 0.0


def test_news_agent_generates_sell_on_strong_bearish_news():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    stub = StubNewsDataClient(
        items_by_symbol={
            "NFLX": [
                NewsItem("NFLX", as_of, "Very bearish", -0.90),
                NewsItem("NFLX", as_of, "Bad outlook", -0.70),
                NewsItem("NFLX", as_of, "Negative guidance", -0.80),
                NewsItem("NFLX", as_of, "Bearish sentiment", -0.75),
                NewsItem("NFLX", as_of, "More concerns", -0.65),
            ]
        }
    )

    agent = NewsAgent(stub, lookback_days=7, limit=10, strong_threshold=0.60, min_confidence_for_signal=0.60)
    sig = agent.generate_signal("NFLX", as_of=as_of)

    assert sig.action == "SELL"
    assert sig.confidence > 0.0


def test_news_agent_holds_when_news_not_strong():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    stub = StubNewsDataClient(
        items_by_symbol={
            "PLTK": [
                NewsItem("PLTK", as_of, "Meh", 0.10),
                NewsItem("PLTK", as_of, "Neutral-ish", -0.05),
                NewsItem("PLTK", as_of, "Still neutral", 0.00),
                NewsItem("PLTK", as_of, "No big change", 0.05),
                NewsItem("PLTK", as_of, "Mixed", -0.10),
            ]
        }
    )

    agent = NewsAgent(stub, lookback_days=7, limit=10, strong_threshold=0.60, min_confidence_for_signal=0.60)
    sig = agent.generate_signal("PLTK", as_of=as_of)

    assert sig.action == "HOLD"
