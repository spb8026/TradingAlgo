import os
import json
import pickle
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

# Cache expiration policies (in days)
CACHE_EXPIRATION = {
    "price_history": 1,          # Price data: 1 day (frequently updated)
    "outstanding_shares_history": 7,  # Shares: 7 days (infrequent changes)
    "market_cap_history": 1,      # Market cap: 1 day (depends on price)
    "free_cash_flow_history": 90,  # Cash flow: 90 days (quarterly updates)
    "free_cash_flow_yield_history": 90  # FCF yield: 90 days (depends on FCF)
}

# Cache directory structure
CACHE_BASE_DIR = Path("data/cache")
STOCKS_CACHE_DIR = CACHE_BASE_DIR / "stocks"


def ensure_cache_directories():
    """Ensure cache directories exist."""
    STOCKS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_stock_cache_path(ticker: str) -> Path:
    """Get the pickle cache file path for a stock."""
    return STOCKS_CACHE_DIR / f"{ticker}.pkl"


def get_stock_meta_path(ticker: str) -> Path:
    """Get the metadata file path for a stock."""
    return STOCKS_CACHE_DIR / f"{ticker}_meta.json"


def get_cache_metadata(ticker: str) -> Optional[Dict]:
    """Load cache metadata for a stock."""
    meta_path = get_stock_meta_path(ticker)
    if not meta_path.exists():
        return None
    
    try:
        with open(meta_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading cache metadata for {ticker}: {e}")
        return None


def save_cache_metadata(ticker: str, metadata: Dict):
    """Save cache metadata for a stock."""
    ensure_cache_directories()
    meta_path = get_stock_meta_path(ticker)
    
    try:
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving cache metadata for {ticker}: {e}")


def is_cache_valid(ticker: str, data_type: str, max_age_days: Optional[int] = None) -> bool:
    """
    Check if cache is valid for a specific data type.
    
    Args:
        ticker: Stock ticker symbol
        data_type: Type of data (e.g., 'price_history', 'free_cash_flow_history')
        max_age_days: Override default expiration (in days)
    
    Returns:
        True if cache exists and is valid, False otherwise
    """
    meta = get_cache_metadata(ticker)
    if meta is None:
        return False
    
    # Check if data type exists in cache
    if data_type not in meta.get("data_available", []):
        return False
    
    # Get expiration policy
    if max_age_days is None:
        max_age_days = CACHE_EXPIRATION.get(data_type, 1)
    
    # Check cache age
    cache_timestamp = meta.get("cache_timestamp")
    if cache_timestamp is None:
        return False
    
    try:
        cache_date = datetime.fromisoformat(cache_timestamp)
        age_days = (datetime.now() - cache_date).days
        return age_days < max_age_days
    except Exception:
        return False


def get_cached_stock(ticker: str) -> Optional[Dict]:
    """
    Load a stock's cached data from pickle file.
    
    Returns:
        Dictionary with stock data attributes, or None if cache doesn't exist
    """
    cache_path = get_stock_cache_path(ticker)
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"⚠️ Error loading cache for {ticker}: {e}")
        return None


def cache_stock(stock) -> bool:
    """
    Save a stock's data to cache.
    
    Args:
        stock: Stock object to cache
    
    Returns:
        True if successful, False otherwise
    """
    ensure_cache_directories()
    cache_path = get_stock_cache_path(ticker=stock.ticker)
    
    # Prepare data dictionary
    stock_data = {
        "ticker": stock.ticker,
        "price_history": getattr(stock, "price_history", None),
        "outstanding_shares_history": getattr(stock, "outstanding_shares_history", None),
        "market_cap_history": getattr(stock, "market_cap_history", None),
        "free_cash_flow_history": getattr(stock, "free_cash_flow_history", None),
        "free_cash_flow_yield_history": getattr(stock, "free_cash_flow_yield_history", None),
        "cash_flow": getattr(stock, "cash_flow", None),
    }
    
    # Determine which data types are available
    data_available = []
    for key in ["price_history", "outstanding_shares_history", "market_cap_history", 
                "free_cash_flow_history", "free_cash_flow_yield_history"]:
        value = stock_data.get(key)
        if value is not None:
            if isinstance(value, pd.Series) and len(value) > 0:
                data_available.append(key)
            elif not isinstance(value, pd.Series) and value:
                data_available.append(key)
    
    # Save pickle file
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(stock_data, f)
    except Exception as e:
        print(f"⚠️ Error saving cache for {stock.ticker}: {e}")
        return False
    
    # Save metadata
    metadata = {
        "ticker": stock.ticker,
        "cache_timestamp": datetime.now().isoformat(),
        "data_available": data_available,
        "cache_version": "1.0"
    }
    save_cache_metadata(stock.ticker, metadata)
    
    return True


def clear_cache(ticker: Optional[str] = None):
    """
    Clear cache for a specific stock or all stocks.
    
    Args:
        ticker: Stock ticker to clear, or None to clear all
    """
    if ticker:
        # Clear specific stock
        cache_path = get_stock_cache_path(ticker)
        meta_path = get_stock_meta_path(ticker)
        
        if cache_path.exists():
            cache_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        
        print(f"✅ Cleared cache for {ticker}")
    else:
        # Clear all stocks
        if STOCKS_CACHE_DIR.exists():
            for file in STOCKS_CACHE_DIR.glob("*.pkl"):
                file.unlink()
            for file in STOCKS_CACHE_DIR.glob("*_meta.json"):
                file.unlink()
            print(f"✅ Cleared all stock caches")


def get_stocks_needing_update(tickers: List[str], force: bool = False) -> Dict[str, List[str]]:
    """
    Determine which stocks need updates and which data types need refreshing.
    
    Args:
        tickers: List of stock tickers to check
        force: If True, mark all stocks as needing update
    
    Returns:
        Dictionary mapping ticker to list of data types that need updating
    """
    updates_needed = {}
    
    for ticker in tickers:
        if force:
            # Force update all data types
            updates_needed[ticker] = list(CACHE_EXPIRATION.keys())
            continue
        
        # Check each data type
        needs_update = []
        meta = get_cache_metadata(ticker)
        
        if meta is None:
            # No cache exists, need all data
            needs_update = list(CACHE_EXPIRATION.keys())
        else:
            # Check each data type
            for data_type, max_age in CACHE_EXPIRATION.items():
                if not is_cache_valid(ticker, data_type, max_age):
                    needs_update.append(data_type)
        
        if needs_update:
            updates_needed[ticker] = needs_update
    
    return updates_needed


def migrate_json_cache_to_pickle(json_file_path: str) -> bool:
    """
    Migrate existing JSON cache to new pickle format.
    
    Args:
        json_file_path: Path to existing JSON cache file
    
    Returns:
        True if migration successful, False otherwise
    """
    if not os.path.exists(json_file_path):
        print(f"⚠️ JSON cache file not found: {json_file_path}")
        return False
    
    try:
        # Import here to avoid circular dependency
        from universe import readUniverseFromFile
        
        print(f"📦 Migrating JSON cache from {json_file_path}...")
        universe = readUniverseFromFile(json_file_path)
        
        migrated_count = 0
        for stock in universe:
            if cache_stock(stock):
                migrated_count += 1
        
        print(f"✅ Migrated {migrated_count} stocks to pickle cache format")
        return True
    except Exception as e:
        print(f"⚠️ Error during migration: {e}")
        return False

