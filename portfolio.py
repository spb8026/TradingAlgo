import os
import pandas as pd
from tradelogger import log_trade


class Portfolio:
    def __init__(self, cash: float, name):
        self.cash = cash
        self.name = name
        self.holdings = {}  # ticker -> {"stock": Stock, "shares": int}
        self.trade_log = []
        self.holdings_history = []
        self.value_history = []

    def get_portfolio_value(self, date):
        total_value = self.cash
        for info in self.holdings.values():
            total_value += info["shares"] * info["stock"].get_price_at_date(date)
        return total_value

    def buy_stock(self, stock, shares, date):
        """Buy shares of a stock and log the trade."""
        price = stock.get_price_at_date(date)
        cost = shares * price
        if cost > self.cash:
            shares = self.cash // price
            cost = shares * price

        self.cash -= cost
        if stock.ticker not in self.holdings:
            self.holdings[stock.ticker] = {"stock": stock, "shares": shares}
        else:
            self.holdings[stock.ticker]["shares"] += shares
        self.trade_log.append(log_trade("BUY", stock, shares, date))

    def sell_stock(self, stock, shares, date):
        """Sell shares of a stock and log the trade."""
        if stock.ticker not in self.holdings:
            return
        owned = self.holdings[stock.ticker]["shares"]
        shares = min(shares, owned)

        price = stock.get_price_at_date(date)
        revenue = shares * price
        self.cash += revenue
        self.holdings[stock.ticker]["shares"] -= shares

        if self.holdings[stock.ticker]["shares"] == 0:
            del self.holdings[stock.ticker]

        self.trade_log.append(log_trade("SELL", stock, shares, date))

    def rebalance_portfolio_with_weights(self, holdings_and_weights, date):
        """Rebalance portfolio based on target weights."""
        date = pd.to_datetime(date).normalize()
        total_value = self.get_portfolio_value(date)

        for stock, target_weight in holdings_and_weights.items():
            target_value = total_value * target_weight
            current_value = 0.0
            if stock.ticker in self.holdings:
                current_value = self.holdings[stock.ticker]["shares"] * stock.get_price_at_date(date)
            price = stock.get_price_at_date(date)

            if target_value > current_value:
                shares_to_buy = ((target_value - current_value) / price)
                if shares_to_buy > 0:
                    self.buy_stock(stock, shares_to_buy, date)
            elif current_value > target_value:
                shares_to_sell = ((current_value - target_value) / price)
                if shares_to_sell > 0:
                    self.sell_stock(stock, shares_to_sell, date)

        # Save snapshots
        self.holdings_history.append((date, self.holdings.copy()))
        self.value_history.append((date, self.get_portfolio_value(date)))

    def export_to_csv(self, directory="exports"):
        """Export holdings, value, and trades to CSV files."""
        os.makedirs(directory, exist_ok=True)

        # Holdings History
        holdings_records = []
        for date, holdings_snapshot in self.holdings_history:
            record = {"date": date}
            for ticker, info in holdings_snapshot.items():
                stock = info["stock"]
                record[ticker] = info["shares"] * stock.get_price_at_date(date)
            holdings_records.append(record)

        if holdings_records:
            pd.DataFrame(holdings_records).sort_values("date").to_csv(
                os.path.join(directory, self.name + "holdings_history.csv"), index=False
            )

        # Value History
        if self.value_history:
            pd.DataFrame(self.value_history, columns=["date", "total_value"]).sort_values("date").to_csv(
                os.path.join(directory, self.name + "value_history.csv"), index=False
            )

        # Trade Log
        if self.trade_log:
            pd.DataFrame(self.trade_log).to_csv(
                os.path.join(directory, self.name + "trade_log.csv"), index=False
            )

        print(f"✅ Portfolio data exported to '{directory}/'")
