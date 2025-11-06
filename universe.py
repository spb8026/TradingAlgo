import os
import json
import pandas as pd
import requests
import yfinance as yf
from typing import List
from stock import Stock


def series_to_dict(series: pd.Series):
    """Convert a pandas Series to a JSON-safe dictionary."""
    if series is None or len(series) == 0:
        return None
    return {
        "dates": series.index.strftime("%Y-%m-%d").tolist(),
        "values": [float(x) if pd.notna(x) else None for x in series.tolist()],
    }


def dict_to_series(data):
    """Reconstruct a pandas Series from a JSON-safe dictionary."""
    if data is None:
        return None
    dates = pd.to_datetime(data["dates"], errors="coerce").tz_localize(None)
    values = data["values"]
    return pd.Series(values, index=dates)



def writeUniverseToFile(universe: List[Stock], file_path: str):
    """Save all relevant Stock data to JSON to avoid refetching."""
    data = []

    for stock in universe:
        stock_data = {
            "ticker": stock.ticker,
            "price_history": series_to_dict(stock.price_history),
            "outstanding_shares_history": series_to_dict(stock.outstanding_shares_history),
            "market_cap_history": series_to_dict(stock.market_cap_history),
            "free_cash_flow_history": series_to_dict(
                getattr(stock, "free_cash_flow_history", None)
            ),
        }
        data.append(stock_data)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Universe saved to {file_path} with {len(data)} stocks.")


def readUniverseFromFile(file_path: str) -> List[Stock]:
    """Load cached universe and reconstruct full Stock objects."""
    with open(file_path, "r") as f:
        data = json.load(f)

    universe = []
    for item in data:
        # Create Stock object without triggering initialization
        stock = object.__new__(Stock)
        stock.ticker = item["ticker"]
        stock.yTicker = yf.Ticker(stock.ticker)

        stock.price_history = dict_to_series(item.get("price_history"))
        stock.outstanding_shares_history = dict_to_series(item.get("outstanding_shares_history"))
        stock.market_cap_history = dict_to_series(item.get("market_cap_history"))
        stock.free_cash_flow_history = dict_to_series(item.get("free_cash_flow_history"))
        stock.cash_flow = None  # optional placeholder

        universe.append(stock)

    print(f"✅ Universe loaded from {file_path} with {len(universe)} stocks.")
    return universe


class S_and_P500:
    file_path = "data/sp500_universe.json"

    @staticmethod
    def initlize_universe():
        """Initialize or load cached S&P 500 universe."""
        if os.path.exists(S_and_P500.file_path) and os.path.getsize(S_and_P500.file_path) > 0:
            return readUniverseFromFile(S_and_P500.file_path)
        else:
            tickers = S_and_P500.get_sp500_tickers()
            universe = [Stock(ticker) for ticker in tickers]
            writeUniverseToFile(universe, S_and_P500.file_path)
            return universe

    @staticmethod
    def get_sp500_tickers() -> List[str]:
        """Fetch current S&P 500 constituent list from Wikipedia."""
        print("📈 Fetching S&P 500 constituent list from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            tables = pd.read_html(response.text)

            sp500 = next((tbl for tbl in tables if "Symbol" in tbl.columns), None)
            if sp500 is None:
                print("⚠️ Could not find S&P 500 table on Wikipedia page.")
                return []

            tickers = [str(t).replace(".", "-") for t in sp500["Symbol"].tolist()]
            print(f"✅ Successfully fetched {len(tickers)} S&P 500 tickers.")
            return tickers

        except Exception as e:
            print(f"⚠️ Error fetching S&P 500 tickers: {e}")
            return []


# Optional test run
if __name__ == "__main__":
    universe = S_and_P500.initlize_universe()
    print(f"Universe loaded: {len(universe)} stocks")
