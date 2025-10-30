class Holding:
    def __init__(self, ticker, quantity):
        self.ticker = ticker
        self.quantity = quantity
        self.weight = 0.0  # Weight in the portfolio
        self.value = 0.0   # Market value of the holding
        