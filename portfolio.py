import os
import pandas as pd
from tradelogger import log_trade


class Portfolio:
    def __init__(self, cash: float, name: str):
        """
        Initialize a portfolio with a starting cash balance and a name.
        """
        self.cash = cash
        self.name = name
        self.holdings = {}  # ticker -> {"stock": Stock, "shares": float}
        self.trade_log = []  # list of trade entries from log_trade()
        self.holdings_history = []  # list of (date, holdings_snapshot)
        self.value_history = []  # list of (date, total_value)
        self.percent_change_history = []  # list of (date, percent_change)


    # ------------------------------------------------------------
    # Portfolio value and trading
    # ------------------------------------------------------------
    def get_portfolio_value(self, date: pd.Timestamp) -> float:
        """
        Compute the total value (cash + holdings) of the portfolio on a given date.
        """
        total_value = self.cash
        for info in self.holdings.values():
            total_value += info["shares"] * info["stock"].get_price_at_date(date)
        return total_value

    def buy_stock(self, stock, shares: float, date: pd.Timestamp):
        """
        Buy shares of a stock and log the trade.
        """
        price = stock.get_price_at_date(date)
        cost = shares * price

        # Adjust shares if insufficient cash
        if cost > self.cash:
            shares = self.cash // price
            cost = shares * price

        if shares <= 0:
            return

        self.cash -= cost
        if stock.ticker not in self.holdings:
            self.holdings[stock.ticker] = {"stock": stock, "shares": shares}
        else:
            self.holdings[stock.ticker]["shares"] += shares

        self.trade_log.append(log_trade("BUY", stock, shares, date))

    def sell_stock(self, stock, shares: float, date: pd.Timestamp):
        """
        Sell shares of a stock and log the trade.
        """
        if stock.ticker not in self.holdings:
            return

        owned = self.holdings[stock.ticker]["shares"]
        shares = min(shares, owned)

        if shares <= 0:
            return

        price = stock.get_price_at_date(date)
        revenue = shares * price
        self.cash += revenue
        self.holdings[stock.ticker]["shares"] -= shares

        if self.holdings[stock.ticker]["shares"] == 0:
            del self.holdings[stock.ticker]

        self.trade_log.append(log_trade("SELL", stock, shares, date))

    # ------------------------------------------------------------
    # Portfolio rebalancing and history
    # ------------------------------------------------------------
    def rebalance_portfolio_with_weights(self, holdings_and_weights: dict, date: pd.Timestamp):
        """
        Rebalance portfolio based on target stock weights.
        holdings_and_weights: {stock_obj: target_weight}
        """
        date = pd.to_datetime(date).normalize()
        total_value = self.get_portfolio_value(date)

        for stock, target_weight in holdings_and_weights.items():
            target_value = total_value * target_weight
            current_value = 0.0
            if stock.ticker in self.holdings:
                current_value = self.holdings[stock.ticker]["shares"] * stock.get_price_at_date(date)

            price = stock.get_price_at_date(date)

            if target_value > current_value:
                shares_to_buy = (target_value - current_value) / price
                if shares_to_buy > 0:
                    self.buy_stock(stock, shares_to_buy, date)
            elif current_value > target_value:
                shares_to_sell = (current_value - target_value) / price
                if shares_to_sell > 0:
                    self.sell_stock(stock, shares_to_sell, date)

        # Save snapshots
        self.holdings_history.append((date, self.holdings.copy()))
        self.value_history.append((date, self.get_portfolio_value(date)))

    def initialize_smooth_value_history(self, increment='D'):
        """
        Generate a smooth daily (or periodic) value history between first and last rebalance dates.
        """
        if not self.value_history:
            return []

        # Ensure sorted by date
        self.value_history.sort(key=lambda x: x[0])
        start_date = self.value_history[0][0]
        end_date = self.value_history[-1][0]

        # Create date range and build dataframe
        full_dates = pd.date_range(start=start_date, end=end_date, freq=increment)
        df = pd.DataFrame(self.value_history, columns=["date", "total_value"]).set_index("date")

        # Interpolate smoothly between known dates
        df = df.reindex(full_dates).interpolate(method="time")

        # Update in list-of-tuples format
        self.value_history = list(df.itertuples(index=True, name=None))

        return self.value_history
    
    @staticmethod
    def price_to_percent_change(old_price: float, new_price: float) -> float:
        """
        Convert a price change to a percent change.
        
        Example:
            old_price = 100
            new_price = 110
            -> returns 10.0  (representing +10%)

        Args:
            old_price (float): Initial price
            new_price (float): Updated price

        Returns:
            float: Percent change (positive for gain, negative for loss)
        """
        if old_price == 0 or old_price is None or new_price is None:
            return 0.0
        return ((new_price - old_price) / old_price) * 100
    
    def initialize_percent_change_history(self):
        """
        Compute and store the percent change history based on the smoothed portfolio value history.
        Must be called after `initialize_smooth_value_history()`.

        Each entry is (date, percent_change) where percent_change represents
        the percentage change from the previous period.
        """
        if not self.value_history or len(self.value_history) < 2:
            print("Not enough data in value history to compute percent changes.")
            return []

        # Convert to DataFrame for convenience
        df = pd.DataFrame(self.value_history, columns=["date", "total_value"]).set_index("date")

        # Compute daily (or per-step) percent change
        df["percent_change"] = df["total_value"].pct_change() * 100

        # Drop NaN (first row)
        df = df.dropna()

        # Store as list of tuples
        self.percent_change_history = list(df[["percent_change"]].itertuples(index=True, name=None))

        return self.percent_change_history



    # ------------------------------------------------------------
    # Export utilities
    # ------------------------------------------------------------
    def export_to_csv(self, directory="exports"):
        """
        Export portfolio holdings, value history, and trade log to CSV files.
        """
        os.makedirs(directory, exist_ok=True)
        self.initialize_smooth_value_history()
        self.initialize_percent_change_history()

        # Holdings history export
        holdings_records = []
        for date, holdings_snapshot in self.holdings_history:
            record = {"date": date}
            for ticker, info in holdings_snapshot.items():
                stock = info["stock"]
                record[ticker] = info["shares"] * stock.get_price_at_date(date)
            holdings_records.append(record)

        if holdings_records:
            pd.DataFrame(holdings_records).sort_values("date").to_csv(
                os.path.join(directory, f"{self.name}_holdings_history.csv"), index=False
            )

        # Value history export
        if self.value_history:
            pd.DataFrame(self.value_history, columns=["date", "total_value"]).sort_values("date").to_csv(
                os.path.join(directory, f"{self.name}_value_history.csv"), index=False
            )

        # Trade log export
        if self.trade_log:
            pd.DataFrame(self.trade_log).to_csv(
                os.path.join(directory, f"{self.name}_trade_log.csv"), index=False
            )
                # Percent Change History export
        if self.percent_change_history:
            pd.DataFrame(self.percent_change_history, columns=["date", "percent_change"]).sort_values("date").to_csv(
                os.path.join(directory, f"{self.name}_percent_change_history.csv"), index=False
            )


        print(f"✅ Portfolio data exported to '{directory}/'")
