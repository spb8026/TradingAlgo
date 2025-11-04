class Holding:
    def __init__(self, ticker, share_amount):
        self.ticker = ticker
        self.share_amount = share_amount
        self.value = 0.0   # Market value of the holding
        