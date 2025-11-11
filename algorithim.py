import pandas as pd
from tradelogger import log_trade
from portfolio import Portfolio
class Algorithim:
    def __init__(self, universe, name= 'BaseAlgorithim', starting_capital=10000):
        self.universe = universe  
        self.current_holdings = {}  # maps ticker -> {"stock": stock_obj, "shares": int}
        self.trade_log = []
        self.name = name
        self.portfolio =  Portfolio(cash=starting_capital, name=self.name)
        

    def backTest(self, start_date, end_date, args=None,  rebalance_frequency=None, rebalance_dates=None,):
        if rebalance_frequency is not None: ## Rebalance at regular intervals
            delta = pd.DateOffset(months=rebalance_frequency)
            current_date = pd.to_datetime(start_date).normalize()
            end_date = pd.to_datetime(end_date).normalize()
            while current_date <= end_date:
                if (args is None):
                    stocks_and_weights = self.get_stocks_and_weights(date)
                else:
                    stocks_and_weights = self.get_stocks_and_weights(date, args)
                print("Rebalancing on:", current_date.date())
                for stock, weight in stocks_and_weights.items():
                    print(f"Date: {current_date.date()}, Stock: {stock.ticker}, Target Weight: {weight}")
                self.portfolio.rebalance_portfolio_with_weights(stocks_and_weights, current_date)
                current_date += delta
        elif rebalance_dates is not None: ## Rebalance at specific dates
            for date in rebalance_dates:
                date = pd.to_datetime(date).normalize()
                if (args is None):
                    stocks_and_weights = self.get_stocks_and_weights(date)
                else:
                    stocks_and_weights = self.get_stocks_and_weights(date, args)
                print("Rebalancing on:", date.date())
                for stock, weight in stocks_and_weights.items():
                    print(f"Date: {date.date()}, Stock: {stock.ticker}, Target Weight: {weight}")
                self.portfolio.rebalance_portfolio_with_weights(stocks_and_weights, date)

        else:
            raise ValueError("Either rebalance_frequency or reblance_dates must be provided.")
        self.portfolio.export_to_csv()
        return self.portfolio.holdings_history, self.portfolio.value_history
        
    
    def get_stocks_and_weights(self, date):
        raise NotImplementedError
    

    



class TestHighestPriceStrategy(Algorithim):
    def __init__(self, universe, initial_capital=10000):
        """Initialize the strategy with a stock universe and initial capital."""
        super().__init__(universe=universe, starting_capital=initial_capital)
        self.name = "TestHighestPriceStrategy"
            
    def get_stocks_and_weights(self, date, top_n=10):
        """Select the top N highest-priced stocks with valid prices and assign equal weights."""
        # Get (stock, price) pairs and filter out None values
        valid_stocks = [
            (stock, price)
            for stock in self.universe
            if (price := stock.get_price_at_date(date)) is not None
        ]

        if not valid_stocks:
            return {}

        # Sort by price descending
        top_stocks = sorted(valid_stocks, key=lambda x: x[1], reverse=True)[:top_n]

        # Equal weights for top stocks
        weight = 1 / len(top_stocks)
        return {stock: weight for stock, _ in top_stocks}


        
    
                

    