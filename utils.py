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
    
import matplotlib.pyplot as plt
import pandas as pd

def plot_portfolio_performance(portfolio, show_percent_change=True, rolling_window=None):
    """
    Plot the portfolio's value history and optional percent change history.

    Args:
        portfolio: Portfolio object with value_history and (optionally) percent_change_history
        show_percent_change (bool): Whether to display the percent change subplot.
        rolling_window (int, optional): If set, adds a rolling average line for smoothing.
    """
    if not portfolio.value_history or len(portfolio.value_history) < 2:
        print("Portfolio value history is empty or insufficient to plot.")
        return

    # Convert to DataFrame for easier handling
    df_value = pd.DataFrame(portfolio.value_history, columns=["date", "total_value"]).set_index("date")
    df_value = df_value.sort_index()

    # Create figure
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(df_value.index, df_value["total_value"], label="Total Value", color="steelblue", linewidth=2)

    # Rolling average for smoothing
    if rolling_window:
        df_value["rolling_avg"] = df_value["total_value"].rolling(window=rolling_window).mean()
        ax1.plot(df_value.index, df_value["rolling_avg"], label=f"{rolling_window}-Day Rolling Avg", linestyle="--", color="orange")

    ax1.set_title(f"Portfolio Performance: {portfolio.name}", fontsize=14)
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Total Value (USD)")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(loc="upper left")

    # Add percent change as a secondary plot
    if show_percent_change and getattr(portfolio, "percent_change_history", None):
        df_pct = pd.DataFrame(portfolio.percent_change_history, columns=["date", "percent_change"]).set_index("date")
        df_pct = df_pct.sort_index()

        ax2 = ax1.twinx()
        ax2.plot(df_pct.index, df_pct["percent_change"], color="limegreen", alpha=0.7, label="% Change")
        ax2.set_ylabel("Percent Change (%)")
        ax2.axhline(0, color="gray", linestyle="--", alpha=0.5)
        ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.show()

