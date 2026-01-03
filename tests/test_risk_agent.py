from algotrader.agents.risk_agent import RiskAgent


def test_allows_buy_within_cap():
    ra = RiskAgent(max_position_pct=0.25)
    d = ra.evaluate(symbol="PLTR", equity=100_000, position_value=10_000, proposed_trade_value=5_000)
    assert d.allow_trade is True


def test_blocks_buy_exceeding_cap():
    ra = RiskAgent(max_position_pct=0.25)
    d = ra.evaluate(symbol="PLTR", equity=100_000, position_value=20_000, proposed_trade_value=6_000)
    assert d.allow_trade is False


def test_allows_sell_even_if_above_cap():
    ra = RiskAgent(max_position_pct=0.25)
    d = ra.evaluate(symbol="PLTR", equity=100_000, position_value=40_000, proposed_trade_value=-5_000)
    assert d.allow_trade is True


def test_rejects_invalid_equity():
    ra = RiskAgent(max_position_pct=0.25)
    d = ra.evaluate(symbol="PLTR", equity=0, position_value=0, proposed_trade_value=1_000)
    assert d.allow_trade is False
