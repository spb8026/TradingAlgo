import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

from utils import ensure_tz_naive

class Stock:
    def __init__(self, ticker):
        self.ticker = ticker
        self.yTicker = yf.Ticker(ticker)
        self.price_history = None
        self.outstanding_shares_history = None
        self.market_cap_history = None
        self.cash_flow = None
        self.free_cash_flow_history = None      
        self.free_cash_flow_yield_history = None
        self.initialize_all()


    def initialize_all(self):
        self.initialize_price_history()
        self.initialize_outstanding_shares_history(start=pd.Timestamp.today() - pd.DateOffset(years=5))
        self.initialize_market_cap_history()
        self.initialize_free_cash_flow_history()
        self.initialize_free_cash_flow_yield_history()

        
        
    def initialize_price_history(self, period="5y", interval="1d"):
        df = self.yTicker.history(period=period, interval=interval)
        df.index = ensure_tz_naive(df.index)
        self.price_history = df["Close"]


    def get_price_at_date(self, date):
        date = pd.to_datetime(date).tz_localize(None).normalize()
        self.price_history = ensure_tz_naive(self.price_history)
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
        self.outstanding_shares_history = ensure_tz_naive(series.dropna())



    def initialize_market_cap_history(self):
        self.market_cap_history = {}
        for date, shares in self.outstanding_shares_history.items():
            price = self.get_price_at_date(date)
            if price is not None:
                self.market_cap_history[date] = price * shares
        self.market_cap_history = pd.Series(self.market_cap_history)
        self.market_cap_history.index = pd.to_datetime(self.market_cap_history.index).tz_localize(None)


    def get_market_cap_at_date(self, date):
        date = pd.to_datetime(date).tz_localize(None).normalize()
        self.market_cap_history = ensure_tz_naive(self.market_cap_history)
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
        
        
    def initialize_free_cash_flow_history(self, period="annual"):
        cf = self.yTicker.quarterly_cashflow
        if cf is None or cf.empty:
            print(f"No cash flow data for {self.ticker}")
            return None
        self.cash_flow = cf.T
        series = pd.Series(self.cash_flow.get("Free Cash Flow")).dropna()
        self.free_cash_flow_history = ensure_tz_naive(series)
    
    def initialize_free_cash_flow_yield_history(self):
        """Compute FCF yield (FCF / Market Cap) for overlapping dates."""
        if self.free_cash_flow_history is None or self.market_cap_history is None:
            return

        # Align on nearest previous market cap date
        yield_series = {}
        for date, fcf in self.free_cash_flow_history.items():
            cap = self.get_market_cap_at_date(date)
            if cap is not None and cap > 0:
                yield_series[date] = fcf / cap

        self.free_cash_flow_yield_history = ensure_tz_naive(pd.Series(yield_series))

    def get_free_cash_flow_at_date(self, date):
        if not hasattr(self, 'free_cash_flow_history'):
            self.initialize_free_cash_flow_history()

        date = pd.to_datetime(date).normalize()
        try:
            return self.free_cash_flow_history.loc[date]
        except KeyError:
            valid_dates = self.free_cash_flow_history.index
            nearest = valid_dates[valid_dates <= date].max()
            if pd.isna(nearest):
                return None
            return self.free_cash_flow_history.loc[nearest]
        
    def get_free_cash_flow_yield_at_date(self, date):
        """Return FCF yield (FCF / Market Cap) at the given date."""
        if self.free_cash_flow_yield_history is None or self.free_cash_flow_yield_history.empty:
            self.initialize_free_cash_flow_yield_history()

        date = pd.to_datetime(date).normalize()
        valid_dates = self.free_cash_flow_yield_history.index
        try:
            return self.free_cash_flow_yield_history.loc[date]
        except KeyError:
            nearest = valid_dates[valid_dates <= date].max()
            if pd.isna(nearest):
                return None
            return self.free_cash_flow_yield_history.loc[nearest]
        
        
    def calculate_theta(self, start=None, end=None):
        """
        Calculate theta = standard deviation of daily price returns over a given period.
        
        Args:
            start (str or Timestamp, optional): start date (inclusive)
            end (str or Timestamp, optional): end date (inclusive)
        Returns:
            float: standard deviation of daily returns (theta)
        """
        if self.price_history is None:
            self.initialize_price_history()

        # Get subset of prices
        prices = self.price_history.copy()
        prices.index = pd.to_datetime(prices.index).tz_localize(None)

        if start:
            start = pd.to_datetime(start).tz_localize(None)
            prices = prices[prices.index >= start]
        if end:
            end = pd.to_datetime(end).tz_localize(None)
            prices = prices[prices.index <= end]

        if len(prices) < 2:
            print("Not enough data to calculate theta.")
            return None

        # Calculate daily percentage returns
        returns = prices.pct_change().dropna()

        # Standard deviation of returns (daily)
        theta = returns.std()

        return theta


        
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
