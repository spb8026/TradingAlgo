import trade
from datetime import datetime
from stockinfo import StockInfo, normalize_price_series
import pandas as pd
import matplotlib.pyplot as plt


class Backtester:
    def __init__(self, strategy, start_date, end_date, initial_balance=100000):
        self.strategy = strategy
        # coerce start/end to datetimes if dates provided
        if isinstance(start_date, datetime):
            self.start_date = start_date
        else:
            self.start_date = pd.to_datetime(start_date)
        if isinstance(end_date, datetime):
            self.end_date = end_date
        else:
            self.end_date = pd.to_datetime(end_date)
        self.balance = initial_balance
        self.portfolio_value = []  # [(date, total_value)]
        self.current_prices = {}   # latest prices for held stocks

    def _normalize_prices(self, prices):
        # Delegate to shared helper
        return normalize_price_series(prices)

    def _get_all_stocks(self):
        """Get stock list from strategy (for ones like CashflowTop10Strategy)."""
        if hasattr(self.strategy, "get_target_stocks"):
            return self.strategy.get_target_stocks()
        elif hasattr(self.strategy, "current_holdings"):
            if isinstance(self.strategy.current_holdings, dict):
                return list(self.strategy.current_holdings.values())
            return self.strategy.current_holdings
        return []

    def _calculate_portfolio_value(self):
        """Compute current portfolio value (cash + holdings)."""
        holdings_value = 0
        for ticker, stock in self.strategy.current_holdings.items():
            # use shares when available
            shares = getattr(stock, 'shares', None)
            price = self.current_prices.get(ticker)
            if price is None:
                try:
                    price = stock.info.get_latest_price()
                except Exception:
                    price = 0
            if shares:
                holdings_value += price * shares
            else:
                # if shares not known, skip (or treat as 0)
                continue
        return self.balance + holdings_value

    def run(self, stocks=None):
        print(f"Running backtest from {self.start_date} to {self.end_date}\n")

        # Ensure we have stocks to start with
        stocks = stocks or self._get_all_stocks()
        if not stocks:
            print("\u26a0\ufe0f No stocks found. Calling strategy to initialize portfolio...")
            self.strategy.rebalance([], date=self.start_date, mode="backtest")
            stocks = self._get_all_stocks()

        if not stocks:
            print("\u274c Strategy did not produce any holdings. Exiting.")
            return

        # Collect normalized price series per stock
        price_series = {}
        for stock in stocks:
            try:
                raw = stock.info.get_price("1y", "1d")
                iterable = self._normalize_prices(raw)
                # keep only dates within range
                iterable = [d for d in iterable if (pd.to_datetime(d['date']) >= pd.to_datetime(self.start_date)) and (pd.to_datetime(d['date']) <= pd.to_datetime(self.end_date))]
                if not iterable:
                    print(f"\u26a0\ufe0f No price data for {stock.ticker} in range")
                    continue
                # sort by date
                iterable.sort(key=lambda x: x['date'])
                price_series[stock.ticker] = iterable
            except Exception as e:
                print(f"\u26a0\ufe0f Failed to parse price data for {stock.ticker}: {e}")
                continue

        if not price_series:
            print("\u26a0\ufe0f No price series available for any stocks. Exiting.")
            return

        # Build sorted list of all dates across series
        all_dates = set()
        for ser in price_series.values():
            for row in ser:
                all_dates.add(pd.to_datetime(row['date']))
        all_dates = sorted(d for d in all_dates if (d >= pd.to_datetime(self.start_date) and d <= pd.to_datetime(self.end_date)))

        print(f"Tracking {len(price_series)} tickers over {len(all_dates)} dates...")

        # iterate date-by-date and update latest prices, then call strategy.rebalance once per date
        for date in all_dates:
            # update prices available at this date
            for ticker, ser in price_series.items():
                # find the price record for this exact date if present
                matches = [r for r in ser if pd.to_datetime(r['date']) == pd.to_datetime(date)]
                if matches:
                    self.current_prices[ticker] = matches[-1]['close']

            # Let strategy rebalance once per date (strategy should be lightweight)
            try:
                # Provide portfolio context to strategy if it accepts it (best-effort)
                try:
                    self.strategy.rebalance(stocks, date=date, mode="backtest", portfolio_value=self._calculate_portfolio_value())
                except TypeError:
                    # older strategies may not accept portfolio_value; call without it
                    self.strategy.rebalance(stocks, date=date, mode="backtest")
            except Exception as e:
                print(f"\u26a0\ufe0f Strategy rebalance error on {date}: {e}")

            # Calculate portfolio value once for this date
            total_value = self._calculate_portfolio_value()
            self.portfolio_value.append((date.to_pydatetime(), total_value))

        print("\nBacktest complete.\n")
        print(f"Recorded {len(self.portfolio_value)} portfolio value points.")

        # Plot results
        self.plot_portfolio_value()

    def plot_portfolio_value(self):
        if not self.portfolio_value:
            print("\u26a0\ufe0f No data to plot.")
            return

        dates, values = zip(*self.portfolio_value)
        plt.figure(figsize=(10, 5))
        plt.plot(dates, values, label="Portfolio Value", linewidth=2)
        plt.title("Portfolio Value Over Time")
        plt.xlabel("Date")
        plt.ylabel("Value ($)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        try:
            out_file = "portfolio_value.png"
            plt.savefig(out_file)
            print(f"Saved portfolio chart to {out_file}")
        except Exception as e:
            print(f"Failed to save plot: {e}")

