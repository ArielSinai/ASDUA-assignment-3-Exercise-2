import pytest
from algotrader.agents.ml_predictor_agent import MLPredictorAgent, PricePrediction


def test_predictor_insufficient_data():
    agent = MLPredictorAgent()
    result = agent.predict("TEST", [100.0])
    
    assert result.symbol == "TEST"
    assert result.confidence == 0.0
    assert result.direction == "NEUTRAL"
    assert "Insufficient data" in result.reason


def test_predictor_bullish_trend():
    agent = MLPredictorAgent(lookback_window=5, confidence_threshold=0.5)
    prices = [100, 102, 104, 106, 108, 110, 112, 115]
    result = agent.predict("TEST", prices)
    
    assert result.symbol == "TEST"
    assert result.predicted_price > prices[-1]
    assert result.direction in ["BULLISH", "NEUTRAL"]


def test_predictor_bearish_trend():
    agent = MLPredictorAgent(lookback_window=5, confidence_threshold=0.5)
    prices = [115, 112, 110, 108, 106, 104, 102, 100]
    result = agent.predict("TEST", prices)
    
    assert result.symbol == "TEST"
    assert result.predicted_price < prices[-1]
    assert result.direction in ["BEARISH", "NEUTRAL"]


def test_predictor_flat_trend():
    agent = MLPredictorAgent(lookback_window=5, confidence_threshold=0.5)
    prices = [100.0] * 10
    result = agent.predict("TEST", prices)
    
    assert result.symbol == "TEST"
    assert result.direction == "NEUTRAL"


def test_predictor_train_insufficient_data():
    agent = MLPredictorAgent(lookback_window=20)
    result = agent.train([100, 101, 102], epochs=1)
    
    assert result is False


def test_predictor_train_with_data():
    agent = MLPredictorAgent(lookback_window=10)
    prices = [100 + i*0.5 for i in range(50)]
    result = agent.train(prices, epochs=1)
    
    assert isinstance(result, bool)


def test_predictor_confidence_bounds():
    agent = MLPredictorAgent()
    prices = [100 + i for i in range(25)]
    result = agent.predict("TEST", prices)
    
    assert 0.0 <= result.confidence <= 1.0


def test_predictor_price_change_calculation():
    agent = MLPredictorAgent(lookback_window=5)
    prices = [100, 101, 102, 103, 104, 105]
    result = agent.predict("TEST", prices)
    
    assert result.predicted_price > 0
    assert "change:" in result.reason.lower()
