import pandas as pd

def ensure_tz_naive(series_or_index):
    """
    Ensure a pandas Series or DatetimeIndex is timezone-naive and normalized.

    Args:
        series_or_index (pd.Series or pd.DatetimeIndex)
    Returns:
        A sanitized copy with tz-naive normalized timestamps.
    """
    if series_or_index is None or len(series_or_index) == 0:
        return series_or_index

    # Convert to datetime if not already
    if isinstance(series_or_index, pd.Series):
        idx = pd.to_datetime(series_or_index.index, errors="coerce").tz_localize(None)
        return pd.Series(series_or_index.values, index=idx)

    elif isinstance(series_or_index, pd.DatetimeIndex):
        return pd.to_datetime(series_or_index, errors="coerce").tz_localize(None)

    else:
        return pd.to_datetime(series_or_index, errors="coerce").tz_localize(None)
