import os
from typing import List
import pandas as pd
import requests
from stock import Stock
import json
import yfinance as yf


def writeUniverseToFile(universe: List[Stock], file_path: str):
    """Save universe with price history to avoid refetching."""
    data = []
    for stock in universe:
        stock_data = {
            'ticker': stock.ticker,
            'price_history': None
        }
        
        # Convert price_history Series to a format JSON can handle
        if stock.price_history is not None:
            stock_data['price_history'] = {
                'dates': stock.price_history.index.strftime('%Y-%m-%d').tolist(),
                'prices': stock.price_history.tolist()
            }
        
        data.append(stock_data)
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Universe saved to {file_path}")


def readUniverseFromFile(file_path: str) -> List[Stock]:
    """Load universe and reconstruct Stock objects with cached price history."""
    with open(file_path, "r") as f:
        data = json.load(f)
    
    universe = []
    for item in data:
        # Create Stock object without triggering __init__ to avoid refetching
        stock = object.__new__(Stock)
        stock.ticker = item['ticker']
        stock.yTicker = yf.Ticker(stock.ticker)
        
        # Reconstruct price_history from saved data
        if item['price_history'] is not None:
            dates = pd.to_datetime(item['price_history']['dates'])
            prices = item['price_history']['prices']
            stock.price_history = pd.Series(prices, index=dates)
        else:
            stock.price_history = None
        
        universe.append(stock)
    
    return universe

class  S_and_P500():
    
    file_path = "data/sp500_tickers.json"
    
    def initlize_universe():
        if os.path.exists(S_and_P500.file_path) and os.path.getsize(S_and_P500.file_path) > 0:
            universe = readUniverseFromFile(S_and_P500.file_path)
        else:
            tickers = S_and_P500.get_sp500_tickers()
            universe = [Stock(ticker) for ticker in tickers]
            writeUniverseToFile(universe, S_and_P500.file_path)
        return universe
    
    @staticmethod
    def get_sp500_tickers() -> List[str]:
        """Fetch current S&P 500 constituent list from Wikipedia."""
        print("Fetching S&P 500 constituent list from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            tables = pd.read_html(response.text)
            # try to find the table that contains 'Symbol' column
            sp500 = None
            for tbl in tables:
                if 'Symbol' in tbl.columns:
                    sp500 = tbl
                    break
            if sp500 is None:
                print("Could not find S&P 500 table on Wikipedia page")
                return []
            # Convert ticker format (handle special characters)
            tickers = [str(t).replace('.', '-') for t in sp500['Symbol'].to_list()]
            print(f"Successfully fetched {len(tickers)} S&P 500 tickers")
            return tickers
        except Exception as e:
            print(f"Error fetching S&P 500 tickers: {e}")
            return []
        
S_and_P500.initlize_universe()