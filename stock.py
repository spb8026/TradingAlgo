import yfinance as yf
import pandas as pd

class Stock:
    def __init__(self, ticker):
        self.ticker = ticker
        self.yTicker = yf.Ticker(ticker)
        self.price_history = None
        self.initialize_all()

    def initialize_all(self):
        self.initialize_price_history()

    def initialize_price_history(self, period="5y", interval="1d"):
        df = yf.Ticker(self.ticker).history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index).tz_localize(None)  # consistent dates
        self.price_history = df['Close']

    def get_price_at_date(self, date):
        if self.price_history is None:
            self.initialize_price_history()

        date = pd.to_datetime(date).normalize()  # normalize input

        try:
            return self.price_history.loc[date]
        except KeyError:
            # fallback to nearest prior date
            valid_dates = self.price_history.index
            nearest = valid_dates[valid_dates <= date].max()
            if pd.isna(nearest):
                return None
            return self.price_history.loc[nearest]

    def get_value_at_date(self, date, shares):
        price = self.get_price_at_date(date)
        return price * shares if price is not None else 0

        
    def initialize_cash_flow_history(self):
        #TODO: implement cash flow history initialization
        pass
    
    def initlize_market_cap_history(self):
        #TODO: implement market cap history initialization
        pass    


test = Stock("AAPL")
print(test.price_history)

