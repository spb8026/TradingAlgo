from tradelogger import log_trade

class Algorithim:
    def __init__(self, universe):
        self.universe = universe  
        self.current_holdings = {}  # maps ticker -> {"stock": stock_obj, "shares": int}
        self.trade_log = []      

    def initlize(self):
        raise NotImplementedError

    def backTest(self):
        raise NotImplementedError


class TestHighestPriceStrategy(Algorithim):
    def __init__(self, universe):
        super().__init__(universe=universe)
        self.name = "TestHighestPriceStrategy"
                
    def rebalance(self, date, shares_to_buy=10):
        new_stocks = self.get_top_stocks(date)

        # Buy new stocks
        for stock in new_stocks:
            if stock.ticker not in self.current_holdings:
                self.current_holdings[stock.ticker] = {"stock": stock, "shares": shares_to_buy}
                self.trade_log.append(log_trade("BUY", stock, shares_to_buy, date))
            else:
                # Optionally, increase holdings if already owned
                self.current_holdings[stock.ticker]["shares"] += shares_to_buy
                self.trade_log.append(log_trade("BUY", stock, shares_to_buy, date))

        # Sell stocks not in new top list
        for ticker in list(self.current_holdings.keys()):
            if ticker not in [s.ticker for s in new_stocks]:
                holding = self.current_holdings[ticker]
                self.trade_log.append(log_trade("SELL", holding["stock"], holding["shares"], date))
                del self.current_holdings[ticker]
        
    def get_top_stocks(self, date, n=10):
        self.universe.sort(key=lambda stock: stock.price_history.loc[date], reverse=True)
        return self.universe[:n]
    
    def get_portfolio_value(self, date):
        total_value = 0
        for holding in self.current_holdings():
            total_value += holding.get_value_at_date(date)
            
    def get_portfolio_weights(self, date):
        total_value = self.get_portfolio_value(date)
        weights = {}
        for ticker, holding in self.current_holdings.items():
            value = holding["stock"].get_value_at_date(date, holding["shares"])
            weights[ticker] = value / total_value if total_value > 0 else 0
        return weights
        
    def backTest(self, start, end, interval):
        holding_history = []
        value_history = []
        current_date = start
        while current_date <= end:
            self.rebalance(current_date)
            holding_snapshot = {ticker: data["shares"] for ticker, data in self.current_holdings.items()}
            holding_history.append((current_date, holding_snapshot))
            value_history.append((current_date, self.get_portfolio_value(current_date)))
            current_date += interval
        return holding_history, value_history
    
    def print_trade_log(self):
        from tradelogger import print_full_log
        print_full_log(self.trade_log)
    
    def plot_performance(self, value_history):
        import matplotlib.pyplot as plt
        dates, values = zip(*value_history)
        plt.plot(dates, values)
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value")
        plt.title(f"Portfolio Value Over Time - {self.name}")
        plt.show()
        
