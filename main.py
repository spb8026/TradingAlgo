from algorithim import TestHighestPriceStrategy
from universe import S_and_P500
from algorithims.momentum import MomentumStrategy


def main():
    # Initialize the S&P 500 universe (loads from cache or fetches fresh)
    universe = S_and_P500.initlize_universe()
    print(f"Loaded universe with {len(universe)} stocks")

    # Initialize the chosen strategy (Momentum or Test)
    algo = MomentumStrategy(universe)

    # Define your backtest parameters
    start = "2025-01-01"
    end = "2025-12-31"
    rebalance_dates = ["2025-03-21", "2025-09-19"]

    # Run the backtest
    print(f"\nStarting backtest for {algo.name}...")
    holdings_history, value_history = algo.backTest(
        start_date=start,
        end_date=end,
        rebalance_dates=rebalance_dates  
    )

    print("\n✅ Backtest complete!")
    print(f"Portfolio final value history length: {len(value_history)}")
    print(f"Holdings snapshots: {len(holdings_history)}")

if __name__ == "__main__":
    main()

