from algotrader.agents.market_agent import MarketAgent


class StubMarketData:
    def __init__(self, prices_by_symbol):
        self.prices_by_symbol = prices_by_symbol

    def get_last_price(self, symbol: str) -> float:
        return self.prices_by_symbol[symbol][-1]

    def get_recent_prices(self, symbol: str, lookback: int):
        data = self.prices_by_symbol.get(symbol, [])
        return data[-lookback:]


def test_market_agent_buy_when_short_ma_above_long_ma():
    prices = list(range(1, 21))  
    md = StubMarketData({"PLTR": prices})
    agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)

    signal = agent.analyze("PLTR")
    assert signal.action == "BUY"
    assert signal.confidence > 0


def test_market_agent_sell_when_short_ma_below_long_ma():
    prices = list(range(20, 0, -1)) 
    md = StubMarketData({"NFLX": prices})
    agent = MarketAgent(md, short_window=5, long_window=20, threshold=0.001)

    signal = agent.analyze("NFLX")
    assert signal.action == "SELL"
    assert signal.confidence > 0


def test_market_agent_hold_when_not_enough_data():
    prices = [100, 101, 102]  
    md = StubMarketData({"PLTK": prices})
    agent = MarketAgent(md, short_window=2, long_window=5, threshold=0.001)

    signal = agent.analyze("PLTK")
    assert signal.action == "HOLD"
    assert signal.confidence == 0.0
