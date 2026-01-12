import pytest
from algotrader.tools.momentum_tool import calculate_rsi, analyze_momentum


def test_rsi_insufficient_data():
    prices = [100.0, 101.0, 102.0]
    rsi = calculate_rsi(prices, period=14)
    assert rsi == 50.0


def test_rsi_all_gains():
    prices = [100.0 + i for i in range(20)]
    rsi = calculate_rsi(prices, period=14)
    assert rsi == 100.0


def test_rsi_mixed():
    prices = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105, 95, 106, 94, 107, 93]
    rsi = calculate_rsi(prices, period=14)
    assert 0 <= rsi <= 100


def test_momentum_insufficient_data():
    result = analyze_momentum("TEST", [100.0, 101.0])
    assert result.trend == "NEUTRAL"
    assert result.reason == "Insufficient data"


def test_momentum_overbought():
    prices = [100.0 + i*2 for i in range(20)]
    result = analyze_momentum("TEST", prices)
    assert result.trend == "OVERBOUGHT"


def test_momentum_oversold():
    prices = [100.0 - i*2 for i in range(20)]
    result = analyze_momentum("TEST", prices)
    assert result.trend == "OVERSOLD"


def test_momentum_bullish():
    prices = [100.0] * 10 + [101.0, 102.0, 103.0, 104.0, 105.0]
    result = analyze_momentum("TEST", prices)
    assert result.trend in ["BULLISH", "NEUTRAL", "OVERBOUGHT"]


def test_momentum_bearish():
    prices = [100.0] * 10 + [99.0, 98.0, 97.0, 96.0, 95.0]
    result = analyze_momentum("TEST", prices)
    assert result.trend in ["BEARISH", "NEUTRAL", "OVERSOLD"]
