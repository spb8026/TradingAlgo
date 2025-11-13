# main.py
from tradingstrategy import CashflowTop10Strategy
from backtester import Backtester
import datetime

strategy = CashflowTop10Strategy()

start = datetime.datetime(2024, 1, 1)
end = datetime.datetime(2024, 12, 31)

bt = Backtester(strategy, start, end)
bt.run()  # No need to pass stocks — strategy builds them
