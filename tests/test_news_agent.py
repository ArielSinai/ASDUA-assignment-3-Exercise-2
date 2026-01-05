from datetime import datetime, timezone, timedelta

from algotrader.agents.news_agent import NewsAgent
from algotrader.data.news_data import NewsItem, StubNewsDataClient


def test_news_agent_returns_no_news_when_empty():
    stub = StubNewsDataClient(items_by_symbol={})
    agent = NewsAgent(stub, lookback_days=7, limit=10)

    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    insight = agent.analyze("PLTR", as_of=as_of)

    assert insight.symbol == "PLTR"
    assert insight.sentiment == 0.0
    assert insight.confidence == 0.0
    assert insight.headlines == []


def test_news_agent_averages_sentiment_and_sets_confidence():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    items = [
        NewsItem("PLTR", as_of - timedelta(days=1), "Good news", 0.6),
        NewsItem("PLTR", as_of - timedelta(days=2), "Bad news", -0.2),
        NewsItem("PLTR", as_of - timedelta(days=3), "Neutral news", 0.0),
    ]

    stub = StubNewsDataClient(items_by_symbol={"PLTR": items})
    agent = NewsAgent(stub, lookback_days=7, limit=10)

    insight = agent.analyze("PLTR", as_of=as_of)

    assert insight.confidence > 0.0
    assert abs(insight.sentiment - (0.6 - 0.2 + 0.0) / 3) < 1e-9
    assert len(insight.headlines) > 0


def test_news_agent_filters_by_lookback_window():
    as_of = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    items = [
        NewsItem("NFLX", as_of - timedelta(days=1), "Recent", 0.5),
        NewsItem("NFLX", as_of - timedelta(days=10), "Too old", -0.9),
    ]

    stub = StubNewsDataClient(items_by_symbol={"NFLX": items})
    agent = NewsAgent(stub, lookback_days=7, limit=10)

    insight = agent.analyze("NFLX", as_of=as_of)

    assert insight.sentiment == 0.5
    assert "Too old" not in insight.headlines
