# tradingstrategy.py
import trade
from stockinfo import StockInfo, get_sp500_tickers

class TradingStrategy:
    def __init__(self):
        self.current_holdings = {}
    
    def rebalance(self, stocks, date=None, mode="live"):
        raise NotImplementedError("This method should be overridden by subclasses")

class OwnedStock:
    def __init__(self, ticker, target_weight: float = None, shares: float = None):
        """Represents a target or owned stock.

        - target_weight: desired portfolio weight (0.0 - 1.0) used for portfolio construction
        - shares: actual number of shares held (can be None until executed)
        """
        self.ticker = ticker
        self.target_weight = target_weight
        self.shares = shares
        self.info = StockInfo(ticker)

class BasicStrategy(TradingStrategy):
    """Buys stocks not currently held and sells those not in target list."""
    
    def rebalance(self, stocks, date=None, mode="live"):
        target_tickers = [s.ticker for s in stocks]

        # Buy missing holdings: in live mode execute using latest price; in backtest mode
        # the Backtester should compute shares from target_weight and portfolio value.
        for stock in stocks:
            if stock.ticker not in self.current_holdings:
                try:
                    if mode == "live":
                        price = stock.info.get_latest_price()
                        # Interpret quantity as shares when calling trade APIs
                        shares = getattr(stock, 'shares', None) or 0
                        if shares <= 0:
                            # If shares not specified, treat target_weight as fraction of cash
                            # (caller should provide execution context)
                            print(f"Skipping live buy for {stock.ticker} - no shares specified")
                        else:
                            trade.buy_stock_current(stock.ticker, shares, price)
                            stock.shares = shares
                    else:
                        # Backtest: the Backtester execution layer will determine shares and call
                        # trade.buy_stock_at_time. Strategy here only registers intended target.
                        pass

                    self.current_holdings[stock.ticker] = stock
                except Exception as e:
                    print(f"Failed to buy {stock.ticker}: {e}")

        # Sell stocks no longer in portfolio
        for ticker in list(self.current_holdings.keys()):
            if ticker not in target_tickers:
                stock = self.current_holdings[ticker]
                try:
                    if mode == "live":
                        price = stock.info.get_latest_price()
                        shares = getattr(stock, 'shares', 0)
                        if shares > 0:
                            trade.sell_stock_current(ticker, shares, price)
                    else:
                        # Backtest: Backtester should call trade.sell_stock_at_time when executing
                        pass

                    del self.current_holdings[ticker]
                except Exception as e:
                    print(f"Failed to sell {ticker}: {e}")


# Cache S&P 500 tickers to avoid repeated Wikipedia fetches
_SP500_CACHE = None

def get_cached_sp500_tickers():
    """Get S&P 500 tickers with caching."""
    global _SP500_CACHE
    if _SP500_CACHE is None:
        _SP500_CACHE = get_sp500_tickers()
    return _SP500_CACHE


class CashflowTop10Strategy(TradingStrategy):
    """Buys the 10 stocks from the S&P 500 with the highest operating cash flow."""

    def __init__(self):
        super().__init__()
        self.cashflow_cache = {}  # Cache cashflow data to avoid repeated API calls
        self.cache_age = 0  # Track how old the cache is

    def get_cashflow_score(self, ticker):
        """Fetch and compute cashflow strength for a stock."""
        # Return cached value if available
        if ticker in self.cashflow_cache:
            return self.cashflow_cache[ticker]
        
        try:
            info = StockInfo(ticker)
            cashflow_data = info.get_cash_flow()
            
            # Handle different response formats from stockdex
            score = 0
            # pandas.DataFrame (annual series) - prefer common operating cash flow columns
            if hasattr(cashflow_data, 'columns'):
                cols = [c.lower() for c in cashflow_data.columns]
                # try likely names
                for candidate in ('annualoperatingcashflow', 'annualcashflowfromcontinuingoperatingactivities', 'annualcashflowfromcontinuingoperatingactivities'):
                    if candidate in cols:
                        # pick most recent non-null row
                        try:
                            colname = cashflow_data.columns[cols.index(candidate)]
                            vals = cashflow_data[colname].dropna().tolist()
                            if vals:
                                score = vals[0]
                                break
                        except Exception:
                            continue
            elif isinstance(cashflow_data, dict):
                vals = cashflow_data.get("totalCashFromOperatingActivities", [])
                if isinstance(vals, list) and vals:
                    score = vals[0]  # Most recent
                elif isinstance(vals, (int, float)):
                    score = vals
            elif isinstance(cashflow_data, list) and len(cashflow_data) > 0:
                score = cashflow_data[0].get("totalCashFromOperatingActivities", 0)
            
            # Cache the result
            self.cashflow_cache[ticker] = score
            return score
            
        except Exception as e:
            print(f"Failed to get cashflow for {ticker}: {e}")
            self.cashflow_cache[ticker] = 0  # Cache failures as 0 to avoid retrying
            return 0

    def rebalance(self, stocks=None, date=None, mode="live", refresh_cache=False, portfolio_value: float = None):
        """
        Rebalance portfolio based on top 10 S&P 500 stocks by operating cash flow.
        
        Args:
            stocks: Ignored for this strategy
            date: Date for backtesting mode
            mode: "live" or "backtest"
            refresh_cache: If True, clear the cashflow cache and refetch all data
        """
        print("Running CashflowTop10Strategy rebalance...")
        
        # Clear cache if requested (e.g., for monthly rebalancing)
        if refresh_cache:
            self.cashflow_cache.clear()
            self.cache_age = 0

        # 1️⃣ Rank all S&P 500 tickers by cash flow
        sp500_tickers = get_cached_sp500_tickers()
        rankings = []
        
        print(f"Analyzing {len(sp500_tickers)} S&P 500 stocks...")
        for i, ticker in enumerate(sp500_tickers):
            if i % 50 == 0:  # Progress indicator
                print(f"  Processed {i}/{len(sp500_tickers)} stocks...")
            
            score = self.get_cashflow_score(ticker)
            rankings.append((ticker, score))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        top10 = rankings[:10]
        
        print(f"\nTop 10 stocks by operating cash flow:")
        for i, (ticker, score) in enumerate(top10, 1):
            print(f"  {i}. {ticker}: ${score:,.0f}")

        # 2️⃣ Build target portfolio with equal weights (10% each)
        target_stocks = []
        target_tickers = []
        weight_per_stock = 0.1  # 10% each for 10 stocks
        
        for ticker, _ in top10:
            try:
                stock = OwnedStock(ticker=ticker, target_weight=weight_per_stock, shares=None)
                target_stocks.append(stock)
                target_tickers.append(ticker)
            except Exception as e:
                print(f"Failed to create OwnedStock for {ticker}: {e}")

        # 3️⃣ Buy new stocks
        for stock in target_stocks:
            if stock.ticker not in self.current_holdings:
                try:
                    if mode == "live":
                        price = stock.info.get_latest_price()
                        shares = getattr(stock, 'shares', None) or 0
                        if shares <= 0:
                            print(f"Skipping live buy for {stock.ticker} - no shares specified")
                        else:
                            trade.buy_stock_current(stock.ticker, shares, price)
                            stock.shares = shares
                    else:
                        # For backtesting, get price at specific date
                        price_data = stock.info.get_price("1y", "1d")
                        if isinstance(price_data, list):
                            price = price_data[-1]["close"]
                        else:
                            price = price_data.tail(1)["close"].iloc[0]
                        shares = None
                        if portfolio_value and stock.target_weight:
                            dollar = portfolio_value * stock.target_weight
                            try:
                                shares = int(dollar // price) if price and price > 0 else 0
                            except Exception:
                                shares = 0
                        if shares and shares > 0:
                            trade.buy_stock_at_time(stock.ticker, shares, date, price)
                            stock.shares = shares

                    self.current_holdings[stock.ticker] = stock
                    if getattr(stock, 'shares', None):
                        print(f"✓ Bought {stock.ticker} at ${price:.2f} ({stock.shares} shares)")

                except Exception as e:
                    print(f"✗ Failed to buy {stock.ticker}: {e}")

        # 4️⃣ Sell stocks no longer in top 10
        for ticker in list(self.current_holdings.keys()):
            if ticker not in target_tickers:
                stock = self.current_holdings[ticker]
                try:
                    if mode == "live":
                        price = stock.info.get_latest_price()
                        shares = getattr(stock, 'shares', 0)
                        if shares > 0:
                            trade.sell_stock_current(ticker, shares, price)
                    else:
                        price_data = stock.info.get_price("1y", "1d")
                        if isinstance(price_data, list):
                            price = price_data[-1]["close"]
                        else:
                            price = price_data.tail(1)["close"].iloc[0]
                        shares = getattr(stock, 'shares', 0)
                        if shares > 0:
                            trade.sell_stock_at_time(ticker, shares, date, price)

                    del self.current_holdings[ticker]
                    print(f"✓ Sold {ticker} at ${price:.2f}")

                except Exception as e:
                    print(f"✗ Failed to sell {ticker}: {e}")

        print(f"\nRebalance complete. Holding {len(self.current_holdings)} stocks.")