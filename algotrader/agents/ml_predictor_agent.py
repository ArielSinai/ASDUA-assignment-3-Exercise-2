from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass(frozen=True)
class PricePrediction:
    symbol: str
    predicted_price: float
    confidence: float
    direction: str
    reason: str


class MLPredictorAgent:
    def __init__(
        self,
        *,
        lookback_window: int = 20,
        prediction_horizon: int = 1,
        confidence_threshold: float = 0.6,
    ) -> None:
        self.lookback_window = lookback_window
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._scaler = None
    
    def _prepare_data(self, prices: List[float]) -> Optional[np.ndarray]:
        if len(prices) < self.lookback_window:
            return None
        
        data = np.array(prices[-self.lookback_window:]).reshape(1, self.lookback_window, 1)
        return data
    
    def _simple_momentum_predict(self, prices: List[float]) -> tuple[float, float]:
        if len(prices) < 5:
            return prices[-1], 0.0
        
        recent = prices[-5:]
        trend = (recent[-1] - recent[0]) / recent[0]
        
        predicted = prices[-1] * (1 + trend * 0.3)
        confidence = min(0.8, abs(trend) * 10)
        
        return predicted, confidence
    
    def _lstm_predict(self, prices: List[float]) -> tuple[float, float]:
        try:
            import tensorflow as tf
            from tensorflow import keras
            
            if self._model is None:
                self._build_model()
            
            data = self._prepare_data(prices)
            if data is None:
                return self._simple_momentum_predict(prices)
            
            prediction = self._model.predict(data, verbose=0)[0][0]
            
            actual_range = max(prices[-10:]) - min(prices[-10:])
            volatility = actual_range / prices[-1] if prices[-1] > 0 else 0.0
            confidence = max(0.3, min(0.9, 1.0 - volatility))
            
            return float(prediction), float(confidence)
        
        except (ImportError, Exception):
            return self._simple_momentum_predict(prices)
    
    def _build_model(self):
        try:
            import tensorflow as tf
            from tensorflow import keras
            
            model = keras.Sequential([
                keras.layers.LSTM(50, activation='relu', input_shape=(self.lookback_window, 1)),
                keras.layers.Dense(25, activation='relu'),
                keras.layers.Dense(1)
            ])
            
            model.compile(optimizer='adam', loss='mse')
            self._model = model
        
        except ImportError:
            self._model = None
    
    def predict(self, symbol: str, prices: List[float]) -> PricePrediction:
        if len(prices) < 2:
            return PricePrediction(
                symbol=symbol,
                predicted_price=0.0,
                confidence=0.0,
                direction="NEUTRAL",
                reason="Insufficient data",
            )
        
        current_price = prices[-1]
        predicted_price, confidence = self._lstm_predict(prices)
        
        price_change_pct = (predicted_price - current_price) / current_price
        
        if confidence < self.confidence_threshold:
            direction = "NEUTRAL"
        elif price_change_pct > 0.01:
            direction = "BULLISH"
        elif price_change_pct < -0.01:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"
        
        reason = f"Predicted ${predicted_price:.2f} from ${current_price:.2f} (change: {price_change_pct*100:.2f}%)"
        
        return PricePrediction(
            symbol=symbol,
            predicted_price=predicted_price,
            confidence=confidence,
            direction=direction,
            reason=reason,
        )
    
    def train(self, prices: List[float], epochs: int = 10) -> bool:
        if len(prices) < self.lookback_window + self.prediction_horizon:
            return False
        
        try:
            import tensorflow as tf
            
            if self._model is None:
                self._build_model()
            
            X, y = [], []
            for i in range(len(prices) - self.lookback_window - self.prediction_horizon):
                X.append(prices[i:i + self.lookback_window])
                y.append(prices[i + self.lookback_window + self.prediction_horizon - 1])
            
            X = np.array(X).reshape(-1, self.lookback_window, 1)
            y = np.array(y)
            
            self._model.fit(X, y, epochs=epochs, verbose=0, validation_split=0.2)
            return True
        
        except (ImportError, Exception):
            return False
