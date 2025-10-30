class Portfolio:
    def __init__(self, cash: float):
        self.cash = cash
        self.holdings = {}  # key: ticker, value: Holding object
    
    def add_holding(self, holding):
        self.holdings[holding.ticker] = holding
    
    def remove_holding(self, ticker):
        if ticker in self.holdings:
            del self.holdings[ticker]
    
    
    