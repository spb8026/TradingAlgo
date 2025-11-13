# stockinfo.py
from typing import List, Optional
import pandas as pd
import requests
from stockdex import Ticker
from datetime import datetime

# Helper: normalize different price formats to a list of {'date': datetime, 'close': float}
def normalize_price_series(prices) -> List[dict]:
    """Normalize price data into a list of dicts with 'date' (datetime) and 'close' (float).

    Accepts:
    - pandas.DataFrame with a 'Date' or 'date' column and a 'Close' or 'close' column
    - list of dicts with keys 'date'/'Date' and 'close'/'Close'
    - dict of lists: {'date': [...], 'close': [...]} or similar
    Returns empty list on empty/invalid input.
    """
    if prices is None:
        return []

    # DataFrame path
    if isinstance(prices, pd.DataFrame):
        df = prices.copy()
        # try to find date column
        if 'Date' in df.columns and 'date' not in df.columns:
            df.rename(columns={'Date': 'date'}, inplace=True)
        if 'Close' in df.columns and 'close' not in df.columns:
            df.rename(columns={'Close': 'close'}, inplace=True)
        if 'date' not in df.columns or 'close' not in df.columns:
            # try index as date
            try:
                df = df.reset_index()
            except Exception:
                return []
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.to_pydatetime()
        else:
            return []
        records = []
        for _, row in df.iterrows():
            close = row.get('close') if 'close' in row.index else row.get('Close')
            if pd.isna(close):
                continue
            records.append({'date': row['date'], 'close': float(close)})
        return records

    # list of dicts
    if isinstance(prices, list):
        out = []
        for item in prices:
            if not isinstance(item, dict):
                continue
            # support keys: date/Date and close/Close
            date_val = item.get('date') or item.get('Date')
            close_val = item.get('close') or item.get('Close')
            if date_val is None or close_val is None:
                continue
            # parse date if string
            if isinstance(date_val, str):
                try:
                    date_val = datetime.fromisoformat(date_val.split('T')[0])
                except Exception:
                    try:
                        date_val = pd.to_datetime(date_val).to_pydatetime()
                    except Exception:
                        continue
            out.append({'date': date_val, 'close': float(close_val)})
        return out

    # dict-of-lists
    if isinstance(prices, dict):
        date_list = prices.get('date') or prices.get('Date')
        close_list = prices.get('close') or prices.get('Close')
        if not date_list or not close_list:
            return []
        out = []
        for d, c in zip(date_list, close_list):
            if d is None or c is None:
                continue
            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d.split('T')[0])
                except Exception:
                    try:
                        d = pd.to_datetime(d).to_pydatetime()
                    except Exception:
                        continue
            out.append({'date': d, 'close': float(c)})
        return out

    return []

class StockInfo:
    def __init__(self, ticker):
        self.ticker = ticker
        self.stock = Ticker(ticker)
        
    def get_price(self, range="1y", interval="1d"):
        """Get price history for given range and interval."""
        return self.stock.yahoo_api_price(range, interval)
    
    def get_cash_flow(self):
        """Get cash flow data."""
        return self.stock.yahoo_api_cash_flow(format='raw')
    
    def get_latest_price(self):
        """Fetch the most recent close price."""
        prices = self.get_price("5d", "1d")
        normalized = normalize_price_series(prices)
        if not normalized:
            raise ValueError(f"No price data available for {self.ticker}")
        # last record by date
        last = max(normalized, key=lambda x: x['date'])
        return last['close']


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