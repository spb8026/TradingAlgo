from algorithim import TestHighestPriceStrategy
from universe import S_and_P500
from algorithims.momentum import MomentumStrategy
from algorithims.momentumFCF import MomentumFCFStrategy


def main():
    # Initialize the S&P 500 universe (loads from cache or fetches fresh)
    universe = S_and_P500.initlize_universe(False)
    print(f"Loaded universe with {len(universe)} stocks")

    algo = MomentumFCFStrategy(universe, name="MomentumFCFStrategy")
    algo2 = MomentumStrategy(universe, name="MomentumStrategy")

    # Define your backtest parameters
    start = "2024-01-01"
    end = "2025-12-31"
    rebalance_dates = ["2024-03-21", "2024-09-19", "2025-03-21", "2025-09-19"]
    args = {
        "momentum_weight": 0.6,
        "fcf_weight": 0.4
    }

    # Run the backtest
    print(f"\nStarting backtest for {algo.name}...")
    holdings_history, value_history = algo.backTest(
        start_date=start,
        end_date=end,
        args=args,
        rebalance_dates=rebalance_dates  
    )

    print("\n✅ Backtest complete!")
    print(f"Portfolio final value history length: {len(value_history)}")
    print(f"Holdings snapshots: {len(holdings_history)}")
    
    print(f"\nStarting backtest for {algo2.name}...")
    holdings_history, value_history = algo2.backTest(
        start_date=start,
        end_date=end,
        rebalance_dates=rebalance_dates  
    )

    print("\n✅ Backtest complete!")
    print(f"Portfolio final value history length: {len(value_history)}")
    print(f"Holdings snapshots: {len(holdings_history)}")

if __name__ == "__main__":
    main()

