import pytest

from algotrader.tools.calculator_tool import clamp, size_trade_notional


def test_clamp_inside_range():
    assert clamp(5, 0, 10) == 5


def test_clamp_below_range():
    assert clamp(-1, 0, 10) == 0


def test_clamp_above_range():
    assert clamp(999, 0, 10) == 10


def test_size_trade_invalid_equity():
    s = size_trade_notional(
        equity=0,
        max_position_pct=0.1,
        existing_position_value=0,
        desired_trade_usd=1000,
    )
    assert s.notional_usd == 0.0
    assert "Invalid equity" in s.reason


def test_size_trade_no_remaining_capacity():
    s = size_trade_notional(
        equity=100_000,
        max_position_pct=0.1,          # cap = 10,000
        existing_position_value=10_000,
        desired_trade_usd=1000,
    )
    assert s.notional_usd == 0.0
    assert "No remaining capacity" in s.reason


def test_size_trade_caps_to_remaining():
    s = size_trade_notional(
        equity=100_000,
        max_position_pct=0.1,          # cap = 10,000
        existing_position_value=9_700, # remaining = 300
        desired_trade_usd=2_000,
        min_trade_usd=50,
    )
    assert s.notional_usd == 300.0
    assert "Sized under cap" in s.reason


def test_size_trade_trade_too_small_blocked():
    s = size_trade_notional(
        equity=100_000,
        max_position_pct=0.1,          # cap = 10,000
        existing_position_value=9_980, # remaining = 20
        desired_trade_usd=2_000,
        min_trade_usd=50,
    )
    assert s.notional_usd == 0.0
    assert "Trade too small" in s.reason


def test_size_trade_uses_desired_if_under_cap():
    s = size_trade_notional(
        equity=100_000,
        max_position_pct=0.1,          # cap = 10,000
        existing_position_value=0,     # remaining = 10,000
        desired_trade_usd=1_500,
        min_trade_usd=50,
    )
    assert s.notional_usd == 1500.0
