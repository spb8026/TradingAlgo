from stock import Stock

class tradeLog:
    def __init__(self, action, ticker, quantity, date, price):
        self.action = action
        self.ticker = ticker
        self.quantity = quantity
        self.date = date
        self.price = price
    def print_trade_log(trade_entry):
        print(f"{trade_entry.action} {trade_entry.quantity} of {trade_entry.ticker} at {trade_entry.price} on {trade_entry.date}")

def log_trade(action, stock, quantity, date):
    price = stock.get_price_at_date(date)
    trade_entry = tradeLog(action, stock.ticker, quantity, date, price)
    return trade_entry
    


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
    for entry in log:
        tradeLog.print_trade_log(entry)


test()
    
    
    

    
    