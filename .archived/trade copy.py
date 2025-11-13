# trade.py
import datetime

TRADE_LOG = []  # Keeps track of executed trades

def log_trade(action, ticker, quantity, price, date=None, mode="live"):
    date = date or datetime.datetime.now()
    TRADE_LOG.append({
        "action": action,
        "ticker": ticker,
        "quantity": quantity,
        "price": price,
        "date": date,
        "mode": mode
    })
    print(f"[{mode.upper()}] {action.upper()} {quantity} of {ticker} at {price} on {date}")

def buy_stock_current(ticker, quantity, price=None):
    # Live (paper) trade buy at current market price
    if price is None:
        from stockinfo import StockInfo
        price = StockInfo(ticker).get_latest_price()
    log_trade("buy", ticker, quantity, price, mode="live")

def sell_stock_current(ticker, quantity, price=None):
    # Live (paper) trade sell at current market price
    if price is None:
        from stockinfo import StockInfo
        price = StockInfo(ticker).get_latest_price()
    log_trade("sell", ticker, quantity, price, mode="live")

def buy_stock_at_time(ticker, quantity, date, price):
    # Simulated buy of the stock at a specific time during backtest
    log_trade("buy", ticker, quantity, price, date, mode="backtest")

def sell_stock_at_time(ticker, quantity, date, price):
    # Simulated sell of the stock at a specific time during backtest
    log_trade("sell", ticker, quantity, price, date, mode="backtest")
