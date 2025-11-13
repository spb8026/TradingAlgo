from algorithims.momentum import MomentumStrategy
from algorithims.momentumFCF import MomentumFCFStrategy
from universe import S_and_P500
from utils import plot_portfolio_performance
from datetime import datetime

def validate_date(date_str):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_validated_input(prompt, validation_func=None, error_msg="Invalid input. Please try again."):
    """Get user input with validation"""
    while True:
        user_input = input(prompt).strip()
        if validation_func is None or validation_func(user_input):
            return user_input
        print(error_msg)

def get_float_input(prompt, min_val=None, max_val=None):
    """Get validated float input"""
    while True:
        try:
            value = float(input(prompt).strip())
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")

def get_int_input(prompt, min_val=None, max_val=None):
    """Get validated integer input"""
    while True:
        try:
            value = int(input(prompt).strip())
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid integer.")

def select_universe():
    """Handle universe selection"""
    universes = [S_and_P500]
    print("\n" + "="*50)
    print("SELECT UNIVERSE")
    print("="*50)
    
    for i, universe in enumerate(universes, 1):
        print(f"{i}. {universe.__name__}")
    
    choice = get_int_input(
        "\nEnter universe number: ",
        min_val=1,
        max_val=len(universes)
    )
    
    selected_universe = universes[choice - 1]
    print(f"\n✓ Selected: {selected_universe.__name__}")
    
    # Load data
    data_choice = get_validated_input(
        "Load from cache or fetch fresh data? (cache/fresh): ",
        lambda x: x.lower() in ['cache', 'fresh'],
        "Please enter 'cache' or 'fresh'."
    ).lower()
    
    load_from_cache = (data_choice == 'cache')
    if load_from_cache:
        print(f"\n📦 Loading from cache (will update stale data automatically)...")
    else:
        print(f"\n🔄 Fetching fresh data for all stocks (this may take a while)...")
    
    universe_data = selected_universe.initlize_universe(load_from_cache)
    print(f"✓ Loaded universe with {len(universe_data)} stocks\n")
    
    return universe_data

def select_algorithm(universe_data):
    """Handle algorithm selection and configuration"""
    algorithms = {
        "1": {"name": "MomentumStrategy", "class": MomentumStrategy},
        "2": {"name": "MomentumFCFStrategy", "class": MomentumFCFStrategy}
    }
    
    print("\n" + "="*50)
    print("SELECT ALGORITHM")
    print("="*50)
    
    for key, algo in algorithms.items():
        print(f"{key}. {algo['name']}")
    
    algo_choice = get_validated_input(
        "\nEnter algorithm number: ",
        lambda x: x in algorithms.keys(),
        "Please enter a valid algorithm number."
    )
    
    # Get algorithm parameters
    algo_name = input("\nEnter a name for this backtest: ").strip()
    initial_capital = get_float_input("Enter initial capital: $", min_val=0)
    
    # Initialize algorithm
    selected_algo = algorithms[algo_choice]
    algo = selected_algo["class"](universe_data, name=algo_name, initial_capital=initial_capital)
    
    # Get algorithm-specific parameters
    args = None
    if algo_choice == "2":  # MomentumFCFStrategy
        print("\n--- Strategy Weights ---")
        momentum_weight = get_float_input(
            "Enter momentum weight (0 to 1): ",
            min_val=0,
            max_val=1
        )
        args = {
            "momentum_weight": momentum_weight,
            "fcf_weight": 1 - momentum_weight
        }
        print(f"✓ FCF weight automatically set to: {args['fcf_weight']:.2f}")
    
    return algo, args

def get_backtest_dates():
    """Get and validate backtest date range"""
    print("\n" + "="*50)
    print("BACKTEST PERIOD")
    print("="*50)
    
    start_date = get_validated_input(
        "Enter start date (YYYY-MM-DD): ",
        validate_date,
        "Invalid date format. Use YYYY-MM-DD."
    )
    
    end_date = get_validated_input(
        "Enter end date (YYYY-MM-DD): ",
        validate_date,
        "Invalid date format. Use YYYY-MM-DD."
    )
    
    return start_date, end_date

def get_rebalance_schedule():
    """Get rebalancing schedule from user"""
    print("\n" + "="*50)
    print("REBALANCE SCHEDULE")
    print("="*50)
    print("1. Frequency-based (every N months)")
    print("2. Specific dates")
    
    mode = get_validated_input(
        "\nEnter option (1 or 2): ",
        lambda x: x in ['1', '2'],
        "Please enter 1 or 2."
    )
    
    if mode == '1':
        frequency = get_int_input(
            "Enter rebalance frequency (months): ",
            min_val=1,
            max_val=12
        )
        return {"type": "frequency", "value": frequency}
    else:
        print("Enter rebalance dates separated by commas")
        dates_str = input("Dates (YYYY-MM-DD,YYYY-MM-DD,...): ").strip()
        dates = [d.strip() for d in dates_str.split(',')]
        
        # Validate all dates
        invalid_dates = [d for d in dates if not validate_date(d)]
        if invalid_dates:
            print(f"Invalid dates: {', '.join(invalid_dates)}")
            return get_rebalance_schedule()
        
        return {"type": "dates", "value": dates}

def run_single_backtest():
    """Run a single backtest"""
    print("\n" + "="*50)
    print("SINGLE BACKTEST")
    print("="*50)
    
    # Select universe
    universe_data = select_universe()
    
    # Select and configure algorithm
    algo, args = select_algorithm(universe_data)
    
    # Get backtest parameters
    start_date, end_date = get_backtest_dates()
    rebalance_schedule = get_rebalance_schedule()
    
    # Run backtest
    print("\n" + "="*50)
    print("RUNNING BACKTEST")
    print("="*50)
    print(f"Algorithm: {algo.name}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: ${algo.portfolio.cash:.2f}")
    
    try:
        if rebalance_schedule["type"] == "frequency":
            holdings_history, value_history = algo.backTest(
                start_date=start_date,
                end_date=end_date,
                rebalance_frequency=rebalance_schedule["value"],
                args=args
            )
        else:
            holdings_history, value_history = algo.backTest(
                start_date=start_date,
                end_date=end_date,
                rebalance_dates=rebalance_schedule["value"],
                args=args
            )
        
        # Display results
        print("\n" + "="*50)
        print("BACKTEST RESULTS")
        print("="*50)
        print(f"✓ Backtest complete!")
        print(f"Portfolio value history: {len(value_history)} data points")
        print(f"Holdings snapshots: {len(holdings_history)}")
        
        if value_history:
            final_value = value_history[-1][1]
            initial_value = value_history[0][1]
            total_return = ((final_value - initial_value) / initial_value) * 100
            print(f"Initial Value: ${initial_value:.2f}")
            print(f"Final Value: ${final_value:.2f}")
            print(f"Total Return: {total_return:.2f}%")
        
        # Ask if user wants to plot
        plot_choice = get_validated_input(
            "\nPlot portfolio performance? (y/n): ",
            lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
            "Please enter y or n."
        ).lower()
        
        if plot_choice in ['y', 'yes']:
            rolling_window = get_int_input(
                "Enter rolling window for smoothing (days, default=7): ",
                min_val=1
            )
            plot_portfolio_performance(algo.portfolio, rolling_window=rolling_window)
            
    except Exception as e:
        print(f"\n❌ Error running backtest: {str(e)}")
        import traceback
        traceback.print_exc()

def run_menu():
    """Main menu interface"""
    while True:
        print("\n" + "="*50)
        print("BACKTESTING FRAMEWORK")
        print("="*50)
        print("1. Run Single Backtest")
        print("2. Compare Algorithms")
        print("3. Optimize Algorithm Weights")
        print("4. Exit")
        
        choice = get_validated_input(
            "\nEnter option (1-4): ",
            lambda x: x in ['1', '2', '3', '4'],
            "Please enter a number between 1 and 4."
        )
        
        if choice == '1':
            run_single_backtest()
        elif choice == '2':
            print("\n⚠️  Feature coming soon: Compare Algorithms")
        elif choice == '3':
            print("\n⚠️  Feature coming soon: Optimize Algorithm Weights")
        elif choice == '4':
            print("\nExiting... Goodbye!")
            break
        
        # Ask if user wants to continue
        if choice != '4':
            continue_choice = get_validated_input(
                "\nReturn to main menu? (y/n): ",
                lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                "Please enter y or n."
            ).lower()
            
            if continue_choice in ['n', 'no']:
                print("\nExiting... Goodbye!")
                break

if __name__ == "__main__":
    run_menu()