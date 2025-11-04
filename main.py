from algorithim import TestHighestPriceStrategy
from universe import S_and_P500

def main():
    universe = S_and_P500.initlize_universe()
    algo = TestHighestPriceStrategy(universe)
    algo.backTest(start_date="2023-01-01", end_date="2023-12-31", rebalance_frequency=3)

if __name__ == "__main__":
    main()
