import pandas as pd
from stock import Stock

class tradeLog:
    def __init__(self, action, ticker, quantity, date, price):
        self.action = action
        self.ticker = ticker
        self.quantity = quantity
        self.date = pd.to_datetime(date).normalize()
        self.price = price

    @staticmethod
    def print_trade_log(trade_entry):
        date_str = trade_entry.date.strftime("%Y-%m-%d")
        print(f"{trade_entry.action} {trade_entry.quantity} of {trade_entry.ticker} at {trade_entry.price:.2f} on {date_str}")


def log_trade(action, stock, quantity, date):
    date = pd.to_datetime(date).normalize()
    price = stock.get_price_at_date(date)
    return tradeLog(action, stock.ticker, quantity, date, price)


def print_full_log(trade_log):
    for entry in sorted(trade_log, key=lambda x: x.date):
        tradeLog.print_trade_log(entry)

        
        

def test():
    test_stock = Stock("AAPL")
    print(test_stock.price_history)
    log = []
    log.append(log_trade("BUY", test_stock, 10, "2023-01-15"))
    log.append(log_trade("SELL", test_stock, 5, "2023-02-20"))
    log.append(log_trade("BUY", test_stock, 15, "2023-03-10"))
    log.append(log_trade("SELL", test_stock, 10, "2023-04-05"))
    log.append(log_trade("BUY", test_stock, 20, "2023-05-01"))
    log.append(log_trade("SELL", test_stock, 15, "2023-06-15"))

test()
    
    
    

    
    