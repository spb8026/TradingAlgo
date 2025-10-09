##Collection of Stocks in a Specific Market

from typing import List

import pandas as pd
import requests
from stock import Stock

class  S_and_P500():
    def initlize_universe():
        tickers = S_and_P500.get_sp500_tickers()
        universe = [Stock(ticker) for ticker in tickers]
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