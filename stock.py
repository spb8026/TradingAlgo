import yfinance as yf
class Stock:
    def __init__(self, ticker):
        self.ticker = ticker
        self.yTicker = yf.Ticker(ticker)
        self.price_history = None
        self.cash_flow_history = None
        self.initialize_all()

    def initialize_all(self):
        self.initialize_price_history()

    def initialize_price_history(self, period="5y", interval="1d"):
        self.price_history = yf.Ticker(self.ticker).history(period=period, interval=interval)['Close']
        
        
    def initialize_cash_flow_history(self):
        #TODO: implement cash flow history initialization
        pass
    
    def initlize_market_cap_history(self):
        #TODO: implement market cap history initialization
        pass
    
    def get_price_at_date(self, date):
        if self.price_history is None:
            self.initialize_price_history()
        try:
            return self.price_history.loc[date]
        except KeyError:
            return None
        
    def get_value_at_date(self, date, shares):
        return self.get_price_at_date(date) * shares
    
    


test = Stock("AAPL")
print(test.price_history)

