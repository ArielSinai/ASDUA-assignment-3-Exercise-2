from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool

from algotrader.agents.market_agent import MarketAgent, MarketSignal
from algotrader.agents.news_agent import NewsAgent, NewsInsight
from algotrader.agents.risk_agent import RiskAgent, RiskDecision


@dataclass(frozen=True)
class CrewDecision:
    symbol: str
    signal: MarketSignal
    approved_trade_value: float
    reason: str


class CrewRunner:
    def __init__(
        self,
        *,
        market_agent: MarketAgent,
        news_agent: NewsAgent,
        risk_agent: RiskAgent,
        score_hold_threshold: float = 0.35,
        news_weight: float = 1.20,
    ) -> None:
        self._market = market_agent
        self._news = news_agent
        self._risk = risk_agent
        self._score_hold_threshold = float(score_hold_threshold)
        self._news_weight = float(news_weight)
        
        self._crew = self._create_crew()
    
    def _create_crew(self) -> Crew:
        from algotrader.tools.momentum_tool import analyze_momentum
        
        @tool("analyze_market_technicals")
        def analyze_market_technicals(symbol: str) -> str:
            """Analyze technical indicators and moving averages for a stock symbol."""
            sig = self._market.analyze(symbol)
            return f"Action: {sig.action}, Confidence: {sig.confidence:.2f}, Reason: {sig.reason}"
        
        @tool("analyze_news_sentiment")
        def analyze_news_sentiment(symbol: str) -> str:
            """Analyze recent news sentiment for a stock symbol."""
            insight = self._news.analyze(symbol)
            return f"Sentiment: {insight.sentiment:.2f}, Confidence: {insight.confidence:.2f}, Reason: {insight.reason}"
        
        @tool("calculate_position_sizing")
        def calculate_position_sizing(equity: float, position_value: float, trade_value: float) -> str:
            """Calculate appropriate position size based on risk parameters."""
            rd = self._risk.approve_and_size(
                symbol="TEMP",
                equity=equity,
                position_value=position_value,
                proposed_trade_value=trade_value,
            )
            return f"Allowed: {rd.allow_trade}, Approved: ${rd.approved_trade_value:.2f}, Reason: {rd.reason}"
        
        @tool("analyze_momentum")
        def momentum_analysis(symbol: str) -> str:
            """Analyze price momentum and RSI for a stock symbol."""
            prices = self._market._md.get_recent_prices(symbol, 30)
            result = analyze_momentum(symbol, prices)
            return f"Trend: {result.trend}, RSI: {result.rsi:.1f}, Momentum: {result.momentum_score:.2f}%, Reason: {result.reason}"
        
        market_analyst = Agent(
            role="Market Technical Analyst",
            goal="Analyze price movements and provide trading signals based on technical indicators",
            backstory="Expert in moving averages and technical analysis patterns",
            tools=[analyze_market_technicals, momentum_analysis],
            verbose=False,
            allow_delegation=False,
        )
        
        news_analyst = Agent(
            role="News Sentiment Analyst",
            goal="Analyze news sentiment and provide insights on market mood",
            backstory="Specialist in parsing financial news and extracting sentiment signals",
            tools=[analyze_news_sentiment],
            verbose=False,
            allow_delegation=False,
        )
        
        risk_manager = Agent(
            role="Risk Manager",
            goal="Ensure trades stay within risk limits and calculate appropriate position sizes",
            backstory="Conservative risk manager focused on capital preservation",
            tools=[calculate_position_sizing],
            verbose=False,
            allow_delegation=False,
        )
        
        coordinator = Agent(
            role="Trading Coordinator",
            goal="Synthesize all agent inputs and make final trading decision",
            backstory="Senior trader who combines technical, sentiment, and risk analysis into actionable trades",
            verbose=False,
            allow_delegation=True,
        )
        
        return Crew(
            agents=[market_analyst, news_analyst, risk_manager, coordinator],
            tasks=[],
            verbose=False,
        )

    def decide(
        self,
        symbol: str,
        *,
        equity: float,
        existing_position_value: float,
        default_trade_value_usd: float,
        as_of=None,
        forced_signal: Optional[MarketSignal] = None,
    ) -> CrewDecision:
        if forced_signal is not None:
            base_signal = forced_signal
            insight = None
            market_sig = None
            news_sig = None
            score = 0.0
        else:
            insight = self._news.analyze(symbol, as_of=as_of)
            news_sig = self._news.generate_signal(symbol, as_of=as_of)
            market_sig = self._market.analyze(symbol)

            score = self._score_votes(market_sig, news_sig)
            base_signal = self._score_to_signal(symbol, score, market_sig, news_sig, insight)

        proposed = self._propose_trade_value(
            base_signal,
            existing_position_value=float(existing_position_value),
            default_trade_value_usd=float(default_trade_value_usd),
        )

        rd: RiskDecision = self._risk.approve_and_size(
            symbol=symbol,
            equity=float(equity),
            position_value=float(existing_position_value),
            proposed_trade_value=float(abs(proposed) if base_signal.action == "BUY" else abs(default_trade_value_usd)),
        )

        if base_signal.action == "HOLD":
            return CrewDecision(
                symbol=symbol,
                signal=MarketSignal(symbol=symbol, action="HOLD", confidence=float(base_signal.confidence), reason=base_signal.reason),
                approved_trade_value=0.0,
                reason=base_signal.reason,
            )

        if base_signal.action == "BUY":
            if (not rd.allow_trade) or float(rd.approved_trade_value) <= 0.0:
                final = MarketSignal(symbol=symbol, action="HOLD", confidence=0.0, reason=f"Risk blocked: {rd.reason}")
                return CrewDecision(symbol=symbol, signal=final, approved_trade_value=0.0, reason=f"{final.reason} | base={base_signal.reason}")

            approved_value = float(rd.approved_trade_value)
            reason = f"{base_signal.reason} | risk={rd.reason} | approved_value={approved_value:.2f}"
            return CrewDecision(symbol=symbol, signal=base_signal, approved_trade_value=approved_value, reason=reason)

        sell_value = float(proposed)
        reason = base_signal.reason
        return CrewDecision(symbol=symbol, signal=base_signal, approved_trade_value=sell_value, reason=reason)

    def _propose_trade_value(
        self,
        signal: MarketSignal,
        *,
        existing_position_value: float,
        default_trade_value_usd: float,
    ) -> float:
        if signal.action == "SELL":
            if existing_position_value > 0:
                return -abs(float(existing_position_value))
            return -abs(float(default_trade_value_usd))
        if signal.action == "BUY":
            return abs(float(default_trade_value_usd))
        return 0.0

    def _score_votes(self, market_sig: MarketSignal, news_sig: MarketSignal) -> float:
        def s(sig: MarketSignal) -> float:
            if sig.action == "BUY":
                return 1.0
            if sig.action == "SELL":
                return -1.0
            return 0.0

        market_score = s(market_sig) * float(market_sig.confidence)
        news_score = s(news_sig) * float(news_sig.confidence) * self._news_weight
        return float(market_score + news_score)

    def _score_to_signal(
        self,
        symbol: str,
        score: float,
        market_sig: MarketSignal,
        news_sig: MarketSignal,
        insight: NewsInsight,
    ) -> MarketSignal:
        if abs(float(score)) < self._score_hold_threshold:
            return MarketSignal(
                symbol=symbol,
                action="HOLD",
                confidence=min(1.0, abs(float(score))),
                reason=(
                    f"Consensus HOLD (score={score:.3f}) | "
                    f"market={market_sig.action}:{market_sig.confidence:.2f} | "
                    f"news={news_sig.action}:{news_sig.confidence:.2f}"
                ),
            )

        action = "BUY" if score > 0 else "SELL"
        conf = min(1.0, abs(float(score)))
        return MarketSignal(
            symbol=symbol,
            action=action,
            confidence=conf,
            reason=(
                f"Consensus {action} (score={score:.3f}) | "
                f"market={market_sig.action}:{market_sig.confidence:.2f} | "
                f"news={news_sig.action}:{news_sig.confidence:.2f} | "
                f"sent={float(insight.sentiment):.2f}"
            ),
        )
