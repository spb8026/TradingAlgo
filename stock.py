import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

class Stock:
    def __init__(self, ticker):
        self.ticker = ticker
        self.yTicker = yf.Ticker(ticker)
        self.price_history = None
        self.outstanding_shares_history = None
        self.market_cap_history = None
        self.initialize_all()

    def initialize_all(self):
        self.initialize_price_history()
        self.initialize_outstanding_shares_history(start=pd.Timestamp.today() - pd.DateOffset(years=5))
        self.initialize_market_cap_history()
        
    def initialize_price_history(self, period="5y", interval="1d"):
        df = self.yTicker.history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        self.price_history = df["Close"]

    def get_price_at_date(self, date):
        if self.price_history is None:
            self.initialize_price_history()

        # Convert to timezone-naive Timestamp
        date = pd.to_datetime(date).tz_localize(None).normalize()

        try:
            return self.price_history.loc[date]
        except KeyError:
            valid_dates = self.price_history.index.tz_localize(None)  # ensure same type
            # Only compare date part
            valid_dates = pd.to_datetime(valid_dates).normalize()
            nearest = valid_dates[valid_dates <= date].max()
            if pd.isna(nearest):
                return None
            return self.price_history.loc[nearest]



    def get_value_at_date(self, date, shares):
        price = self.get_price_at_date(date)
        return price * shares if price is not None else 0

    def initialize_outstanding_shares_history(self, start):
        shares_df = self.yTicker.get_shares_full(start="2010-01-01")

        # Some yfinance versions return a Series, others a DataFrame.
        if isinstance(shares_df, pd.DataFrame):
            # Try to infer the correct column
            if "Shares Outstanding" in shares_df.columns:
                series = shares_df["Shares Outstanding"]
            else:
                # Take the first numeric column if column name differs
                series = shares_df.select_dtypes(include='number').iloc[:, 0]
        else:
            # It's already a Series
            series = shares_df

        # Clean up
        self.outstanding_shares_history = series.dropna()


    def initialize_market_cap_history(self):
        self.market_cap_history = {}
        for date, shares in self.outstanding_shares_history.items():
            price = self.get_price_at_date(date)
            if price is not None:
                self.market_cap_history[date] = price * shares
        self.market_cap_history = pd.Series(self.market_cap_history)

    def get_market_cap_at_date(self, date):
        if self.market_cap_history is None:
            self.initialize_market_cap_history()
        date = pd.to_datetime(date).normalize()
        try:
            return self.market_cap_history.loc[date]
        except KeyError:
            valid_dates = self.market_cap_history.index
            nearest = valid_dates[valid_dates <= date].max()
            if pd.isna(nearest):
                return None
            return self.market_cap_history.loc[nearest]
        
    def plot_market_cap_history(self, rolling_window=None):
        """Plot historical market capitalization over time.
        
        Args:
            rolling_window (int, optional): window size for rolling average (in days).
        """
        if self.market_cap_history is None or len(self.market_cap_history) == 0:
            print("Market cap history not initialized.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(self.market_cap_history.index, self.market_cap_history.values, label="Market Cap", color="steelblue")

        # Optional rolling average for smoothing
        if rolling_window:
            rolling = self.market_cap_history.rolling(window=rolling_window).mean()
            plt.plot(rolling.index, rolling.values, label=f"{rolling_window}-Day Rolling Avg", linestyle="--", color="orange")

        plt.title(f"{self.ticker} Market Capitalization Over Time")
        plt.xlabel("Date")
        plt.ylabel("Market Cap (USD)")
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.show()


# Example usage
test = Stock("AAPL")
test.plot_market_cap_history(rolling_window=30)