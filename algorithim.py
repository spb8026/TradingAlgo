import pandas as pd
from tradelogger import log_trade

class Algorithim:
    def __init__(self, universe):
        self.universe = universe  
        self.current_holdings = {}  # maps ticker -> {"stock": stock_obj, "shares": int}
        self.trade_log = []
        self.name = "BaseAlgorithm"
        self.initial_capital = 10000  # Default initial capital

    def initialize(self):
        raise NotImplementedError

    def backTest(self):
        raise NotImplementedError

    # --- Reusable portfolio management methods ---
    
    def get_portfolio_value(self, date):
        """Calculate total portfolio value at a given date."""
        date = pd.to_datetime(date).normalize()
        return sum(h['stock'].get_value_at_date(date, h['shares']) 
                   for h in self.current_holdings.values())

    def get_portfolio_weights(self, date):
        """Calculate portfolio weights for each holding."""
        total_value = self.get_portfolio_value(date)
        weights = {}
        for ticker, holding in self.current_holdings.items():
            value = holding["stock"].get_value_at_date(date, holding["shares"])
            weights[ticker] = value / total_value if total_value > 0 else 0
        return weights

    def buy_stock(self, stock, shares, date):
        """Buy shares of a stock and log the trade."""
        if stock.ticker not in self.current_holdings:
            self.current_holdings[stock.ticker] = {"stock": stock, "shares": shares}
        else:
            self.current_holdings[stock.ticker]["shares"] += shares
        self.trade_log.append(log_trade("BUY", stock, shares, date))

    def sell_stock(self, ticker, date):
        """Sell all shares of a stock and log the trade."""
        if ticker in self.current_holdings:
            holding = self.current_holdings[ticker]
            self.trade_log.append(log_trade("SELL", holding["stock"], holding["shares"], date))
            del self.current_holdings[ticker]

    def rebalance_portfolio(self, new_stocks, date, shares_to_buy=1):
        """Generic rebalancing logic: buy new stocks, sell old ones."""
        # Buy new stocks
        for stock in new_stocks:
            self.buy_stock(stock, shares_to_buy, date)

        # Sell stocks not in new list
        new_tickers = {s.ticker for s in new_stocks}
        for ticker in list(self.current_holdings.keys()):
            if ticker not in new_tickers:
                self.sell_stock(ticker, date)

    def rebalance_portfolio_with_weights(self, stocks_and_weights, date, portfolio_value):
        """
        Rebalance portfolio based on target weights.
        
        Args:
            stocks_and_weights: dict mapping stock objects to target weights (0-1)
            date: rebalancing date
            portfolio_value: total portfolio value to allocate
        """
        date = pd.to_datetime(date).normalize()
        target_tickers = {stock.ticker: stock for stock in stocks_and_weights.keys()}
        
        # Sell stocks not in target portfolio
        for ticker in list(self.current_holdings.keys()):
            if ticker not in target_tickers:
                self.sell_stock(ticker, date)
        
        # Buy/adjust positions based on weights
        for stock, weight in stocks_and_weights.items():
            target_value = portfolio_value * weight
            current_price = stock.price_history.asof(date)
            
            if current_price > 0:
                target_shares = int(target_value / current_price)
                current_shares = self.current_holdings.get(stock.ticker, {}).get("shares", 0)
                
                shares_diff = target_shares - current_shares
                
                if shares_diff > 0:
                    self.buy_stock(stock, shares_diff, date)
                elif shares_diff < 0:
                    # Partial sell (reduce position)
                    self.current_holdings[stock.ticker]["shares"] += shares_diff
                    self.trade_log.append(log_trade("SELL", stock, -shares_diff, date))

    def print_trade_log(self):
        """Print the full trade log."""
        from tradelogger import print_full_log
        print_full_log(self.trade_log)
    
    def plot_performance(self, value_history):
        """Plot portfolio value over time."""
        import matplotlib.pyplot as plt
        dates, values = zip(*value_history)
        plt.plot(dates, values)
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value")
        plt.title(f"Portfolio Value Over Time - {self.name}")
        plt.show()

    def run_backtest(self, start, end, interval="1mo"):
        """Generic backtest framework - calls rebalance() at each interval."""
        start = pd.to_datetime(start).normalize()
        end = pd.to_datetime(end).normalize()
        delta = pd.Timedelta(days=30) if interval == "1mo" else pd.Timedelta(days=7)

        holding_history = []
        value_history = []

        current_date = start
        while current_date <= end:
            self.rebalance(current_date)
            holding_snapshot = {t: d["shares"] for t, d in self.current_holdings.items()}
            holding_history.append((current_date, holding_snapshot))
            portfolio_val = self.get_portfolio_value(current_date)
            if portfolio_val == 0:
                portfolio_val = self.initial_capital
            value_history.append((current_date, portfolio_val))
            current_date += delta

        return holding_history, value_history


class TestHighestPriceStrategy(Algorithim):
    def __init__(self, universe, initial_capital=10000):
        """Initialize the strategy with a stock universe and initial capital."""
        super().__init__(universe=universe)
        self.name = "TestHighestPriceStrategy"
        self.initial_capital = initial_capital
                
    def rebalance(self, date, use_weights=True):
        """Strategy-specific rebalancing logic."""
        if use_weights:
            stocks_and_weights = self.get_top_stocks_and_weights(date, n=10)
            portfolio_value = self.get_portfolio_value(date)
            if portfolio_value == 0:
                portfolio_value = self.initial_capital
            self.rebalance_portfolio_with_weights(stocks_and_weights, date, portfolio_value)
        else:
            new_stocks = self.get_top_stocks(date, n=10)
            self.rebalance_portfolio(new_stocks, date, shares_to_buy=10)
        
    def get_top_stocks(self, date, n=10):
        """Get top N stocks by price at given date (for equal-weight strategy)."""
        date = pd.to_datetime(date).normalize()
        sorted_universe = sorted(self.universe, 
                                key=lambda stock: stock.price_history.asof(date), 
                                reverse=True)
        return sorted_universe[:n]
    
    def get_top_stocks_and_weights(self, date, n=10):
        """
        Get top N stocks by price and calculate weights proportional to their prices.
        
        Returns:
            dict: mapping of stock objects to their weights (normalized to sum to 1)
        """
        date = pd.to_datetime(date).normalize()
        
        # Sort stocks by price (highest first)
        sorted_universe = sorted(self.universe, 
                                key=lambda stock: stock.price_history.asof(date), 
                                reverse=True)
        top_stocks = sorted_universe[:n]
        
        # Calculate weights based on prices
        stocks_and_weights = self.get_stock_weights(top_stocks, date)
        
        return stocks_and_weights
    
    def get_stock_weights(self, stocks, date):
        """
        Calculate normalized weights for stocks based on their prices.
        
        Args:
            stocks: list of stock objects
            date: date to get prices at
            
        Returns:
            dict: mapping of stock objects to normalized weights
        """
        date = pd.to_datetime(date).normalize()
        
        # Get prices for all stocks
        prices = {}
        for stock in stocks:
            price = stock.price_history.asof(date)
            if price > 0:  # Only include stocks with valid prices
                prices[stock] = price
        
        # Calculate total price sum
        total_price = sum(prices.values())
        
        # Normalize weights to sum to 1
        weights = {}
        if total_price > 0:
            for stock, price in prices.items():
                weights[stock] = price / total_price
        
        return weights

    def backTest(self, start, end, interval="1mo"):
        """Run backtest using inherited method."""
        his1, his2 = self.run_backtest(start, end, interval)
        self.print_trade_log()
        return his1, his2
    