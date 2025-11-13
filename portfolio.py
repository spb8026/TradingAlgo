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
        self.holdings_history = {} # date -> holdings snapshot
        self.value_history = []  # list of (date, total_value)
        self.percent_change_history = []  # list of (date, percent_change)


    # ------------------------------------------------------------
    # Portfolio value and trading
    # ------------------------------------------------------------
    def get_portfolio_value(self, date: pd.Timestamp, holdings_at_date=None) -> float:
        """
        Compute the total value (cash + holdings) of the portfolio on a given date.
        """
        total_value = self.cash
        for info in holdings_at_date.values():
            price = info["stock"].get_price_at_date(date)
            if price is not None:
                total_value += info["shares"] * price
        return total_value

    def buy_stock(self, stock, shares: float, date: pd.Timestamp):
        """Buy shares of a stock and log the trade."""
        price = stock.get_price_at_date(date)
        if price is None:
            return
        cost = shares * price

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
        """Sell shares of a stock and log the trade."""
        if stock.ticker not in self.holdings:
            return

        owned = self.holdings[stock.ticker]["shares"]
        shares = min(shares, owned)

        if shares <= 0:
            return

        price = stock.get_price_at_date(date)
        if price is None:
            return

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
        """Rebalance portfolio based on target stock weights."""
        date = pd.to_datetime(date).normalize()
        total_value = self.get_portfolio_value(date, self.holdings)

        for stock, target_weight in holdings_and_weights.items():
            target_value = total_value * target_weight
            current_value = 0.0
            if stock.ticker in self.holdings:
                current_value = self.holdings[stock.ticker]["shares"] * stock.get_price_at_date(date)

            price = stock.get_price_at_date(date)
            if price is None:
                continue

            if target_value > current_value:
                shares_to_buy = (target_value - current_value) / price
                if shares_to_buy > 0:
                    self.buy_stock(stock, shares_to_buy, date)
            elif current_value > target_value:
                shares_to_sell = (current_value - target_value) / price
                if shares_to_sell > 0:
                    self.sell_stock(stock, shares_to_sell, date)

        # Save snapshots
        self.holdings_history[date] = self.holdings.copy()

    # ------------------------------------------------------------
    # Daily tracking
    # ------------------------------------------------------------
    def generate_daily_value_history(self, start_date: pd.Timestamp, end_date: pd.Timestamp):
        """
        Generate and store the portfolio's daily total value between start_date and end_date.
        Uses the most recent holdings snapshot at or before each date.
        """
        start_date = pd.to_datetime(start_date).normalize()
        end_date = pd.to_datetime(end_date).normalize()

        snapshot_dates = sorted(self.holdings_history.keys())
        if not snapshot_dates:
            print("⚠️ No holdings history available.")
            return

        i = 0
        current_holdings = self.holdings_history[snapshot_dates[i]].copy()

        for date in pd.date_range(start_date, end_date):
            # Move to the next snapshot if this date passes it
            while i + 1 < len(snapshot_dates) and date >= snapshot_dates[i + 1]:
                i += 1
                current_holdings = self.holdings_history[snapshot_dates[i]].copy()

            total_value = self.get_portfolio_value(date, holdings_at_date=current_holdings)
            self.value_history.append([date, total_value])


    # ------------------------------------------------------------
    # Percent change utilities
    # ------------------------------------------------------------
    @staticmethod
    def price_to_percent_change(old_price: float, new_price: float) -> float:
        """Convert absolute price change to percent change."""
        if old_price == 0 or old_price is None or new_price is None:
            return 0.0
        return ((new_price - old_price) / old_price) * 100

    def initialize_percent_change_history(self):
        """Compute % change from daily value history."""
        if not self.value_history or len(self.value_history) < 2:
            print("Not enough data to compute percent changes.")
            return []

        df = pd.DataFrame(self.value_history, columns=["date", "total_value"]).set_index("date")
        df["percent_change"] = df["total_value"].pct_change() * 100
        df = df.dropna()

        self.percent_change_history = list(df[["percent_change"]].itertuples(index=True, name=None))
        return self.percent_change_history

    # ------------------------------------------------------------
    # Export utilities
    # ------------------------------------------------------------
    def export_to_csv(self, directory="exports"):
        """Export holdings, value history, and trade log."""
        os.makedirs(directory, exist_ok=True)

        if self.value_history:
            pd.DataFrame(self.value_history, columns=["date", "total_value"]).to_csv(
                os.path.join(directory, f"{self.name}_value_history.csv"), index=False
            )

        if self.percent_change_history:
            pd.DataFrame(self.percent_change_history, columns=["date", "percent_change"]).to_csv(
                os.path.join(directory, f"{self.name}_percent_change_history.csv"), index=False
            )

        if self.holdings_history:
            records = []
            for date, snapshot in self.holdings_history.items():
                record = {"date": date}
                for ticker, info in snapshot.items():
                    stock = info["stock"]
                    record[ticker] = info["shares"] * stock.get_price_at_date(date)
                records.append(record)
            pd.DataFrame(records).to_csv(
                os.path.join(directory, f"{self.name}_holdings_history.csv"), index=False
            )

        # if self.trade_log:
        #     pd.DataFrame(self.trade_log).to_csv(
        #         os.path.join(directory, f"{self.name}_trade_log.csv"), index=False
        #     )

        print(f"✅ Portfolio data exported to '{directory}/'")
