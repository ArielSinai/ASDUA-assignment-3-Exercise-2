from algotrader.agents.exec_agent import ExecAgent
from algotrader.agents.market_agent import MarketSignal
from algotrader.agents.risk_agent import RiskAgent
from algotrader.execution.execution_stub import StubExecutionClient


def test_exec_agent_does_not_trade_on_hold():
    ex = StubExecutionClient()
    ra = RiskAgent(max_position_pct=0.25)
    agent = ExecAgent(ex, ra)

    res = agent.act(MarketSignal("PLTR", "HOLD", 0.3, "flat"), trade_value=1000)
    assert res.executed is False


def test_exec_agent_buys_when_allowed():
    ex = StubExecutionClient(starting_cash=100_000)
    ra = RiskAgent(max_position_pct=0.25)
    agent = ExecAgent(ex, ra)

    res = agent.act(MarketSignal("PLTR", "BUY", 0.8, "up"), trade_value=1000)
    assert res.executed is True
    assert ex.get_position("PLTR") is not None


def test_exec_agent_blocks_when_risk_rejects():
    ex = StubExecutionClient(starting_cash=100_000)
    ra = RiskAgent(max_position_pct=0.01)  # tiny cap
    agent = ExecAgent(ex, ra)

    res = agent.act(MarketSignal("PLTR", "BUY", 0.8, "up"), trade_value=5000)
    assert res.executed is False
