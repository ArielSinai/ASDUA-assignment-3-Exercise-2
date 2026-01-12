from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MomentumResult:
    symbol: str
    momentum_score: float
    rsi: float
    trend: str
    reason: str


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze_momentum(symbol: str, prices: List[float]) -> MomentumResult:
    if len(prices) < 14:
        return MomentumResult(
            symbol=symbol,
            momentum_score=0.0,
            rsi=50.0,
            trend="NEUTRAL",
            reason="Insufficient data",
        )
    
    rsi = calculate_rsi(prices)
    
    recent_change = (prices[-1] - prices[-10]) / prices[-10] if prices[-10] != 0 else 0.0
    momentum_score = recent_change * 100
    
    if rsi > 70:
        trend = "OVERBOUGHT"
    elif rsi < 30:
        trend = "OVERSOLD"
    elif momentum_score > 2:
        trend = "BULLISH"
    elif momentum_score < -2:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    
    return MomentumResult(
        symbol=symbol,
        momentum_score=momentum_score,
        rsi=rsi,
        trend=trend,
        reason=f"RSI={rsi:.1f}, Momentum={momentum_score:.2f}%",
    )
