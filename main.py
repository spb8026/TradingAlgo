from algorithim import TestHighestPriceStrategy
from algorithim import ILoveApple
from universe import S_and_P500

def main():
    universe = S_and_P500.initlize_universe()
    algo = TestHighestPriceStrategy(universe)
    holding_history, value_history = algo.backTest(
        start="2024-01-01",
        end="2024-06-30",
        interval="1mo"
    )
    algo.plot_performance(value_history)

if __name__ == "__main__":
    main()
