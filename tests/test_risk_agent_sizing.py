from algotrader.agents.risk_agent import RiskAgent


def test_approve_and_size_invalid_equity_blocks():
    ra = RiskAgent(max_position_pct=0.1)
    d = ra.approve_and_size(
        symbol="PLTR",
        equity=0,
        position_value=0,
        proposed_trade_value=1000,
    )
    assert d.allow_trade is False
    assert d.approved_trade_value == 0.0


def test_approve_and_size_sell_always_allowed():
    ra = RiskAgent(max_position_pct=0.1)
    d = ra.approve_and_size(
        symbol="PLTR",
        equity=100_000,
        position_value=9_000,
        proposed_trade_value=-2_000,
    )
    assert d.allow_trade is True
    assert d.approved_trade_value == -2_000


def test_approve_and_size_buy_capped_to_remaining():
    ra = RiskAgent(max_position_pct=0.1)  # cap=10,000
    d = ra.approve_and_size(
        symbol="PLTR",
        equity=100_000,
        position_value=9_700,       # remaining=300
        proposed_trade_value=2_000, # wants more
        min_trade_usd=50,
    )
    assert d.allow_trade is True
    assert d.approved_trade_value == 300.0


def test_approve_and_size_buy_too_small_blocked():
    ra = RiskAgent(max_position_pct=0.1)  # cap=10,000
    d = ra.approve_and_size(
        symbol="PLTR",
        equity=100_000,
        position_value=9_980,       # remaining=20
        proposed_trade_value=2_000,
        min_trade_usd=50,
    )
    assert d.allow_trade is False
    assert d.approved_trade_value == 0.0
