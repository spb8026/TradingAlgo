import pandas as pd
import numpy as np
from algorithim import Algorithim

class MomentumStrategy(Algorithim):
    def __init__(self, universe, initial_capital=10000):
        super().__init__(universe=universe, starting_capital=initial_capital)
        self.name = "MomentumStrategy"
        self.prev_constituents = []


    # ------------------------------------------------------------
    # Core momentum calculations
    # ------------------------------------------------------------
    def momentum_value(self, stock, date):
        """Compute the 12-month momentum with fallback per S&P methodology."""
        price_today = stock.get_price_at_date(date - pd.DateOffset(months=2))
        price_past = stock.get_price_at_date(date - pd.DateOffset(months=14))
        if price_past is None:
            price_past = stock.get_price_at_date(date - pd.DateOffset(months=11))
        if price_past is None or price_today is None or price_past <= 0:
            return None
        return (price_today / price_past) ** 0.5 - 1

    def risk_adjusted_momentum_value(self, stock, date, momentum_value):
        """Momentum divided by volatility (theta) over same window."""
        start = date - pd.DateOffset(months=14)
        end = date - pd.DateOffset(months=2)
        theta = stock.calculate_theta(start=start, end=end)
        if theta is None or theta == 0:
            return None
        return momentum_value / theta

    # ------------------------------------------------------------
    # Statistical helpers
    # ------------------------------------------------------------
    @staticmethod
    def get_z_score(value, mean, std):
        if std == 0:
            return 0
        z = (value - mean) / std
        return max(min(z, 3), -3)  # winsorize ±3

    @staticmethod
    def get_momentum_score(z):
        if z > 0:
            return 1 + z
        elif z < 0:
            return 1 / (1 - z)
        else:
            return 1

    # ------------------------------------------------------------
    # Main stock scoring and weighting
    # ------------------------------------------------------------
    def get_stocks_and_weights(self, date):
        """Compute weights for all stocks on a given rebalance date."""
        momentum_data = []

        # Step 1. Compute momentum values for all stocks
        for stock in self.universe:
            try:
                m = self.momentum_value(stock, date)
                if m is None:
                    continue
                ra = self.risk_adjusted_momentum_value(stock, date, m)
                if ra is not None:
                    momentum_data.append({
                        "stock": stock,
                        "ticker": stock.ticker,
                        "momentum_value": m,
                        "risk_adj": ra
                    })
            except Exception:
                continue

        if not momentum_data:
            print("No valid momentum data this period.")
            return {}

        df = pd.DataFrame(momentum_data)

        # Step 2. Compute z-scores and momentum scores
        mean = df["risk_adj"].mean()
        std = df["risk_adj"].std()
        df["z_score"] = df["risk_adj"].apply(lambda x: self.get_z_score(x, mean, std))
        df["momentum_score"] = df["z_score"].apply(self.get_momentum_score)

        # Step 3. Rank and select top 20% using 20% buffer rule
        df = df.sort_values("momentum_score", ascending=False).reset_index(drop=True)
        total_stocks = len(df)
        target_count = int(np.round(total_stocks * 0.2))            # top 20%
        top_80 = int(target_count * 0.8)
        top_120 = min(int(target_count * 1.2), total_stocks)

        # auto-select top 80%
        selected = set(df.iloc[:top_80]["ticker"])

        # re-include previous constituents still in top 120%
        if self.prev_constituents:
            eligible = set(df.iloc[:top_120]["ticker"])
            for t in self.prev_constituents:
                if t in eligible and len(selected) < target_count:
                    selected.add(t)

        # fill remaining slots with next best
        if len(selected) < target_count:
            for t in df.iloc[top_80:target_count]["ticker"]:
                if len(selected) >= target_count:
                    break
                selected.add(t)

        df_selected = df[df["ticker"].isin(selected)]

        # Step 4. Compute reference S&P 500 weights from market caps
        caps = []
        for stock in self.universe:
            cap = stock.get_market_cap_at_date(date)
            if cap is not None:
                caps.append(cap)
        total_cap = sum(caps)
        ref_weights = {
            stock.ticker: stock.get_market_cap_at_date(date) / total_cap
            for stock in self.universe if stock.get_market_cap_at_date(date) is not None
        }

        # Step 5. Compute raw weights (cap × momentum score)
        df_selected["market_cap"] = df_selected["stock"].apply(lambda s: s.get_market_cap_at_date(date))
        df_selected["raw_weight"] = df_selected["market_cap"] * df_selected["momentum_score"]
        total_raw = df_selected["raw_weight"].sum()
        df_selected["uncapped_weight"] = df_selected["raw_weight"] / total_raw

        # Step 6. Apply caps: min(9%, 3×ref weight)
        df_selected["ref_weight"] = df_selected["ticker"].map(ref_weights).fillna(0)
        df_selected["max_weight"] = np.minimum(0.09, 3 * df_selected["ref_weight"])
        df_selected["capped_weight"] = np.minimum(df_selected["uncapped_weight"], df_selected["max_weight"])

        # Step 7. Renormalize after capping
        total_capped = df_selected["capped_weight"].sum()
        df_selected["final_weight"] = df_selected["capped_weight"] / total_capped

        # Update stored constituents for next rebalance (for buffer)
        self.prev_constituents = df_selected["ticker"].tolist()

        # Step 8. Return as {Stock: weight} mapping
        final_weights = {row["stock"]: row["final_weight"] for _, row in df_selected.iterrows()}
        return final_weights

    # ------------------------------------------------------------
    # Helper: decide if rebalance should occur
    # ------------------------------------------------------------
    @staticmethod
    def should_rebalance(date):
        """Rebalance effective March and September (after Feb/Aug reference)."""
        m = pd.Timestamp(date).month
        return m in [3, 9]
