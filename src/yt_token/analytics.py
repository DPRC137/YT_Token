"""Quantitative analytics, pricing models, fair value curves, and simulations for Yield Tokens."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from yt_token.config import QuantitativeParams
from yt_token.models import InvestmentAnalysis, LimitOrderSimulation


def calculate_hours_to_maturity(timestamp: pd.Timestamp | datetime, maturity: datetime) -> float:
    """Calculate remaining time to maturity in hours."""
    if isinstance(timestamp, pd.Timestamp):
        ts = timestamp.to_pydatetime()
    else:
        ts = timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if maturity.tzinfo is None:
        maturity = maturity.replace(tzinfo=timezone.utc)
    return (maturity - ts).total_seconds() / 3600.0


def calculate_yt_price(
    implied_apy: float | pd.Series,
    hours_to_maturity: float | pd.Series,
    annual_hours: float = 8760.0,
) -> float | pd.Series:
    r"""
    Calculate Yield Token (YT) price expressed per unit of underlying asset.

    Mathematical Definition:
    $$P_{YT} = (1 + \text{Implied APY})^{\frac{t_{hours}}{8760}} - 1$$
    """
    time_factor = hours_to_maturity / annual_hours
    return (implied_apy + 1.0) ** time_factor - 1.0


def calculate_long_yield_apy(
    underlying_apy: float | pd.Series,
    implied_apy: float | pd.Series,
    hours_to_maturity: float | pd.Series,
    annual_hours: float = 8760.0,
) -> float | pd.Series:
    r"""
    Calculate the annualized rate of return for going 'Long Yield' (holding YT).

    Mathematical Definition:
    $$\text{Long Yield APY} = \left(1 + \frac{\text{Underlying APY} - \text{Implied APY}}{\text{Implied APY}}\right)^{\frac{8760}{t_{hours}}} - 1$$
    """
    safe_implied = np.where(implied_apy == 0, 1e-6, implied_apy)
    spread_ratio = 1.0 + (underlying_apy - safe_implied) / safe_implied
    safe_spread = np.maximum(spread_ratio, 1e-6)
    safe_hours = np.where(hours_to_maturity == 0, 1e-6, hours_to_maturity)
    annualization_power = annual_hours / safe_hours
    return (safe_spread**annualization_power) - 1.0


def calculate_points_earned(
    yt_price: float | pd.Series,
    time_diff_hours: float | pd.Series,
    points_rate: float,
    underlying_amount: float,
    multiplier: float,
) -> float | pd.Series:
    r"""
    Calculate total incentive points accrued at maturity from investing in YT.

    Mathematical Definition:
    $$\text{Points} = \frac{1}{P_{YT}} \times t_{hours} \times r_{points} \times A_{underlying} \times M_{YT}$$
    """
    safe_price = np.where(yt_price == 0, 1e-6, yt_price)
    leverage = (1.0 / safe_price) * multiplier
    return leverage * time_diff_hours * points_rate * underlying_amount


def calculate_fair_value_curve(
    implied_apy_avg: float,
    time_series: pd.DatetimeIndex,
    maturity_time: datetime,
    annual_hours: float = 8760.0,
) -> pd.Series:
    r"""
    Compute the theoretical Fair Value decay trajectory of YT towards maturity.

    Mathematical Definition:
    $$P_{\text{fair}}(t) = 1 - \frac{1}{(1 + \bar{r})^{\frac{T - t}{8760}}}$$
    """
    if maturity_time.tzinfo is None:
        maturity_time = maturity_time.replace(tzinfo=timezone.utc)
    hours_remaining = (maturity_time - time_series).total_seconds() / 3600.0
    exponent = hours_remaining / annual_hours
    fair_values = 1.0 - (1.0 / ((1.0 + implied_apy_avg) ** exponent))
    return pd.Series(fair_values, index=time_series)


def enrich_market_dataframe(
    df_apy: pd.DataFrame,
    df_ohlcv: pd.DataFrame,
    maturity_time: datetime,
    params: QuantitativeParams | None = None,
) -> tuple[pd.DataFrame, float, pd.DatetimeIndex, np.ndarray]:
    """Merge, align, and compute all financial metrics on APY and OHLCV datasets."""
    p = params or QuantitativeParams()
    if df_apy.empty:
        return pd.DataFrame(), 0.0, pd.date_range("2024-01-01", periods=1), np.array([])

    df = df_apy.copy()
    if df_ohlcv is not None and not df_ohlcv.empty and "Volume" in df_ohlcv.columns:
        # Align volumes if lengths match or merge on Time
        if len(df_ohlcv) == len(df):
            df["volume"] = df_ohlcv["Volume"].values
        else:
            merged = pd.merge_asof(
                df.sort_values("timestamp"),
                df_ohlcv[["Time", "Volume"]].sort_values("Time"),
                left_on="timestamp",
                right_on="Time",
                direction="nearest",
            )
            df["volume"] = merged["Volume"].fillna(0.0)
    else:
        df["volume"] = 1.0

    if maturity_time.tzinfo is None:
        maturity_time = maturity_time.replace(tzinfo=timezone.utc)

    df["hours_to_maturity"] = (maturity_time - df["timestamp"]).dt.total_seconds() / 3600.0
    df["Time"] = pd.to_datetime(df["timestamp"], utc=True)
    df["yt/underlying"] = calculate_yt_price(df["impliedApy"], df["hours_to_maturity"], p.annual_hours)
    df["long_yield_apy"] = calculate_long_yield_apy(
        df["underlyingApy"], df["impliedApy"], df["hours_to_maturity"], p.annual_hours
    )

    time_diff_hours = (maturity_time - df["Time"]).dt.total_seconds() / 3600.0
    df["points"] = calculate_points_earned(
        df["yt/underlying"],
        time_diff_hours,
        p.points_per_hour_per_underlying,
        p.underlying_amount,
        p.pendle_yt_multiplier,
    )

    h_range = pd.date_range(start=df["Time"].iloc[0], end=maturity_time, freq="h", tz="UTC")

    vol_sum = df["volume"].sum()
    if vol_sum > 0:
        implied_apy_average = float((df["impliedApy"] * df["volume"] / vol_sum).sum())
    else:
        implied_apy_average = float(df["impliedApy"].mean())

    hours_curve = (maturity_time - h_range).total_seconds() / 3600.0
    fair_value_curve = 1.0 - 1.0 / ((1.0 + implied_apy_average) ** (hours_curve / p.annual_hours))

    if vol_sum > 0:
        df["weighted_points"] = df["points"] * df["volume"] / vol_sum
    else:
        df["weighted_points"] = df["points"] / len(df)

    df["fair"] = fair_value_curve[: len(df)]
    df["difference"] = df["fair"] - df["yt/underlying"]

    return df, implied_apy_average, h_range, fair_value_curve


def analyze_historical_purchase(
    df: pd.DataFrame,
    purchase_time_dt: datetime,
    maturity_time: datetime,
    params: QuantitativeParams | None = None,
    underlying_invest_amount: float = 1.0,
) -> InvestmentAnalysis | None:
    """Interpolate and evaluate the exact performance of a historical YT purchase."""
    if df.empty:
        return None
    p = params or QuantitativeParams()
    if purchase_time_dt.tzinfo is None:
        purchase_time_dt = purchase_time_dt.replace(tzinfo=timezone.utc)
    if maturity_time.tzinfo is None:
        maturity_time = maturity_time.replace(tzinfo=timezone.utc)

    nearest_times = df["Time"].sort_values().unique()
    prev_series = nearest_times[nearest_times <= purchase_time_dt]
    next_series = nearest_times[nearest_times > purchase_time_dt]

    if len(prev_series) == 0 or len(next_series) == 0:
        # Fallback to closest single point if purchase is at boundaries
        closest_row = df.iloc[(df["Time"] - purchase_time_dt).abs().argsort()[:1]].iloc[0]
        yt_price = float(closest_row["yt/underlying"])
    else:
        prev_time = prev_series.max()
        next_time = next_series.min()
        dist_prev = (purchase_time_dt - prev_time).total_seconds()
        dist_next = (next_time - purchase_time_dt).total_seconds()
        total_dist = dist_prev + dist_next
        if total_dist == 0:
            w_prev, w_next = 0.5, 0.5
        else:
            w_prev = dist_next / total_dist
            w_next = dist_prev / total_dist

        price_prev = df[df["Time"] == prev_time]["yt/underlying"].values[0]
        price_next = df[df["Time"] == next_time]["yt/underlying"].values[0]
        yt_price = float(w_prev * price_prev + w_next * price_next)

    time_diff_hours = (maturity_time - purchase_time_dt).total_seconds() / 3600.0
    safe_price = max(yt_price, 1e-6)
    leverage = (1.0 / safe_price) * p.pendle_yt_multiplier
    points = leverage * time_diff_hours * p.points_per_hour_per_underlying * underlying_invest_amount

    points_per_underlying = points / underlying_invest_amount
    cost_per_point = 1.0 / points_per_underlying if points_per_underlying > 0 else float("inf")

    exceed_count = int(df[df["points"] < points_per_underlying].shape[0])
    total_count = int(df.shape[0])
    percent_exceed = (exceed_count / total_count * 100.0) if total_count > 0 else 0.0

    vol_sum = df["volume"].sum()
    avg_points = float((df["points"] * df["volume"] / vol_sum).sum()) if vol_sum > 0 else float(df["points"].mean())

    return InvestmentAnalysis(
        purchase_time=purchase_time_dt,
        yt_price=yt_price,
        leverage=leverage,
        points_at_maturity=points,
        points_per_underlying=points_per_underlying,
        cost_per_point=cost_per_point,
        market_max_points=float(df["points"].max()),
        market_min_points=float(df["points"].min()),
        market_avg_points=avg_points,
        percentile_outperformed=percent_exceed,
    )


def simulate_limit_order(
    df: pd.DataFrame,
    estimated_time_dt: datetime,
    target_implied_apy: float,
    maturity_time: datetime,
    params: QuantitativeParams | None = None,
    underlying_invest_amount: float = 1.0,
) -> LimitOrderSimulation | None:
    """Model the expected execution and payoff of a pending or future limit order."""
    if df.empty:
        return None
    p = params or QuantitativeParams()
    if estimated_time_dt.tzinfo is None:
        estimated_time_dt = estimated_time_dt.replace(tzinfo=timezone.utc)
    if maturity_time.tzinfo is None:
        maturity_time = maturity_time.replace(tzinfo=timezone.utc)

    hours_remaining = (maturity_time - estimated_time_dt).total_seconds() / 3600.0
    simulated_price = float((target_implied_apy + 1.0) ** (hours_remaining / p.annual_hours) - 1.0)
    safe_price = max(simulated_price, 1e-6)

    leverage = (1.0 / safe_price) * p.pendle_yt_multiplier
    simulated_points = leverage * hours_remaining * p.points_per_hour_per_underlying * underlying_invest_amount
    points_per_underlying = simulated_points / underlying_invest_amount

    vol_sum = df["volume"].sum()
    weighted_sim_points = (
        (df["volume"].mean() / vol_sum) * points_per_underlying if vol_sum > 0 else points_per_underlying
    )
    exceed_count = int(df[df["weighted_points"] < weighted_sim_points].shape[0])
    total_count = int(df.shape[0])
    percent_exceed = (exceed_count / total_count * 100.0) if total_count > 0 else 0.0

    avg_points = float((df["points"] * df["volume"] / vol_sum).sum()) if vol_sum > 0 else float(df["points"].mean())

    return LimitOrderSimulation(
        estimated_time=estimated_time_dt,
        implied_apy=target_implied_apy,
        simulated_price=simulated_price,
        leverage=leverage,
        simulated_points=simulated_points,
        points_per_underlying=points_per_underlying,
        market_max_points=float(df["points"].max()),
        market_min_points=float(df["points"].min()),
        market_avg_points=avg_points,
        percentile_outperformed=percent_exceed,
    )
