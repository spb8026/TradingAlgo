import pandas as pd
import numpy as np
from algorithim import Algorithim

class MomentumFCFStrategy(Algorithim):
    def __init__(self, universe, name=None, initial_capital=10000):
        super().__init__(universe=universe, starting_capital=initial_capital, name=(name or "MomentumFCFStrategy"))
        self.name = name or "MomentumFCFStrategy"
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
    # Free Cash Flow (FCF) calculations
    # ------------------------------------------------------------
    def fcf_yield_value(self, stock, date):
        """
        FCF Yield = Free Cash Flow / Market Cap.
        Falls back to most recent available FCF if none at the rebalance date.
        """
        try:
            fcf = stock.get_free_cash_flow_at_date(date)
            if (fcf is None) and hasattr(stock, "free_cash_flow_history") and getattr(stock, "free_cash_flow_history") is not None:
                # fallback to most recent reported FCF (common early in backtests)
                fcf_hist = stock.free_cash_flow_history
                if not getattr(fcf_hist, "empty", True):
                    fcf = fcf_hist.iloc[0]
            cap = stock.get_market_cap_at_date(date)
            if fcf is None or cap is None or cap <= 0:
                return None
            return float(fcf) / float(cap)
        except Exception as e:
            print(f"⚠️ FCF yield error for {stock.ticker}: {e}")
            return None

    def get_fcf_yield_score(self, fcf_yield_series: pd.Series) -> pd.DataFrame:
        """
        Normalize FCF yields using z-scores and map to yield scores (same mapping as momentum).
        Returns DataFrame with columns: fcf_z, fcf_score
        """
        if fcf_yield_series is None or fcf_yield_series.empty:
            return pd.DataFrame({"fcf_z": pd.Series(dtype=float), "fcf_score": pd.Series(dtype=float)})

        mean = fcf_yield_series.mean()
        std = fcf_yield_series.std()

        def z_score(x):
            if std == 0 or np.isnan(std):
                return 0.0
            z = (x - mean) / std
            # winsorize ±3
            return max(min(z, 3.0), -3.0)

        def fcf_score_from_z(z):
            if z > 0:
                return 1 + z
            elif z < 0:
                return 1 / (1 - z)
            else:
                return 1.0

        z = fcf_yield_series.apply(z_score)
        score = z.apply(fcf_score_from_z)
        return pd.DataFrame({"fcf_z": z, "fcf_score": score})

    # ------------------------------------------------------------
    # Statistical helpers
    # ------------------------------------------------------------
    @staticmethod
    def get_z_score(value, mean, std):
        if std == 0 or np.isnan(std):
            return 0.0
        z = (value - mean) / std
        return max(min(z, 3.0), -3.0)  # winsorize ±3

    @staticmethod
    def get_momentum_score(z):
        if z > 0:
            return 1 + z
        elif z < 0:
            return 1 / (1 - z)
        else:
            return 1.0

    # ------------------------------------------------------------
    # Main stock scoring and weighting
    # ------------------------------------------------------------
    def get_stocks_and_weights(self, date, args):
        """Compute weights for all stocks on a given rebalance date."""
        # safe args
        momentum_w = args.get("momentum_weight", 0.5)
        fcf_w = args.get("fcf_weight", 0.5)
        weight_sum = momentum_w + fcf_w
        if weight_sum <= 0:
            momentum_w, fcf_w, weight_sum = 0.5, 0.5, 1.0

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
            except Exception as e:
                print(f"⚠️ Error computing momentum for {stock.ticker}: {e}")
                continue

        if not momentum_data:
            print(f"[{pd.to_datetime(date).date()}] No valid momentum data this period.")
            return {}

        df = pd.DataFrame(momentum_data)

        # Step 2. Momentum z & score
        mean = df["risk_adj"].mean()
        std = df["risk_adj"].std()
        df["z_score"] = df["risk_adj"].apply(lambda x: self.get_z_score(x, mean, std))
        df["momentum_score"] = df["z_score"].apply(self.get_momentum_score)

        # Step 2b. FCF Yield per stock (with fallback)
        df["fcf_yield"] = df["stock"].apply(lambda s: self.fcf_yield_value(s, date))

        # If absolutely no FCF values, keep df but set zeros so momentum still works
        if df["fcf_yield"].isna().all():
            print(f"[{pd.to_datetime(date).date()}] No valid FCF data — proceeding with momentum only.")
            df["fcf_z"] = 0.0
            df["fcf_score"] = 1.0
        else:
            # Keep rows but fill missing yields with series mean to avoid dropping momentum signals entirely
            fcf_series = df["fcf_yield"].copy()
            fcf_series_filled = fcf_series.fillna(fcf_series.mean())
            fcf_scores_df = self.get_fcf_yield_score(fcf_series_filled)
            # align indices
            fcf_scores_df = fcf_scores_df.set_index(df.index)
            df["fcf_z"] = fcf_scores_df["fcf_z"]
            df["fcf_score"] = fcf_scores_df["fcf_score"]

        # Combine momentum & FCF (normalized by weight sum)
        df["combined_score"] = ((momentum_w * df["z_score"].fillna(0.0)) +
                                (fcf_w * df["fcf_z"].fillna(0.0))) / weight_sum

        # Step 3. Rank and select top 20% using 20% buffer rule
        df = df.sort_values("combined_score", ascending=False).reset_index(drop=True)
        total_stocks = len(df)
        target_count = max(1, int(np.round(total_stocks * 0.2)))  # ensure at least 1
        top_80 = int(target_count * 0.8)
        top_120 = min(int(target_count * 1.2), total_stocks)

        selected = set(df.iloc[:top_80]["ticker"])

        if self.prev_constituents:
            eligible = set(df.iloc[:top_120]["ticker"])
            for t in self.prev_constituents:
                if t in eligible and len(selected) < target_count:
                    selected.add(t)

        if len(selected) < target_count:
            for t in df.iloc[top_80:target_count]["ticker"]:
                if len(selected) >= target_count:
                    break
                selected.add(t)

        df_selected = df[df["ticker"].isin(selected)].copy()

        # Fallback if selection somehow empty
        if df_selected.empty:
            print(f"⚠️ No stocks selected on {pd.to_datetime(date).date()} — reverting to top {target_count} by combined_score.")
            df_selected = df.head(target_count).copy()

        # Step 4. Reference S&P weights from market caps
        caps = []
        for stock in self.universe:
            cap = stock.get_market_cap_at_date(date)
            if cap is not None and cap > 0:
                caps.append(cap)
        if not caps:
            print(f"[{pd.to_datetime(date).date()}] No valid market cap data.")
            return {}

        total_cap = float(sum(caps))
        if total_cap <= 0:
            print(f"[{pd.to_datetime(date).date()}] Total market cap is zero.")
            return {}

        ref_weights = {}
        for stock in self.universe:
            cap = stock.get_market_cap_at_date(date)
            if cap is not None and cap > 0:
                ref_weights[stock.ticker] = float(cap) / total_cap

        # Step 5. Raw weights (cap × **combined_score**)
        df_selected["market_cap"] = df_selected["stock"].apply(lambda s: s.get_market_cap_at_date(date))
        df_selected["market_cap"] = df_selected["market_cap"].fillna(0.0)
        df_selected["raw_weight"] = df_selected["market_cap"].astype(float) * df_selected["combined_score"].astype(float)

        total_raw = df_selected["raw_weight"].sum()
        if total_raw == 0 or np.isnan(total_raw):
            print(f"[{pd.to_datetime(date).date()}] ⚠️ No valid raw weights after scoring.")
            return {}

        df_selected["uncapped_weight"] = df_selected["raw_weight"] / total_raw

        # Step 6. Apply caps: min(9%, 3×ref weight)
        df_selected["ref_weight"] = df_selected["ticker"].map(ref_weights).fillna(0.0)
        df_selected["max_weight"] = np.minimum(0.09, 3.0 * df_selected["ref_weight"])
        df_selected["capped_weight"] = np.minimum(df_selected["uncapped_weight"], df_selected["max_weight"])

        # Step 7. Renormalize after capping
        total_capped = df_selected["capped_weight"].sum()
        if total_capped == 0 or np.isnan(total_capped):
            print(f"[{pd.to_datetime(date).date()}] ⚠️ All capped weights are zero.")
            return {}

        df_selected["final_weight"] = df_selected["capped_weight"] / total_capped

        # Store for buffer on next rebalance
        self.prev_constituents = df_selected["ticker"].tolist()

        # Step 8. Return as {Stock: weight}
        final_weights = {row["stock"]: float(row["final_weight"]) for _, row in df_selected.iterrows()}

        # tiny numerical cleanup to ensure sum ≈ 1
        s = sum(final_weights.values())
        if s > 0 and abs(s - 1.0) > 1e-6:
            final_weights = {k: v / s for k, v in final_weights.items()}

        print(f"[{pd.to_datetime(date).date()}] ✅ Selected {len(final_weights)} stocks. Weight sum: {sum(final_weights.values()):.6f}")
        return final_weights
