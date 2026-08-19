"""Technical analysis engine for Yield Token price and volatility time series."""

import numpy as np
import pandas as pd

from yt_token.config import TechnicalParams


def calculate_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate simple moving average with backward fill for initial warm-up period."""
    if len(series) < window:
        return series.rolling(window=max(1, len(series)), min_periods=1).mean().bfill()
    return series.rolling(window=window, min_periods=1).mean().bfill()


def calculate_volatility(
    series: pd.Series,
    window: int = 48,
    annualize: bool = False,
    annual_periods: int = 8760,
) -> pd.Series:
    """Calculate rolling standard deviation / volatility of series with backward fill."""
    if len(series) < window:
        vol = series.rolling(window=max(2, len(series)), min_periods=2).std().bfill()
    else:
        vol = series.rolling(window=window, min_periods=2).std().bfill()
    if annualize:
        vol = vol * np.sqrt(annual_periods)
    return vol


def calculate_rsi(series: pd.Series, window: int = 72) -> pd.Series:
    r"""
    Calculate Relative Strength Index (RSI).

    Mathematical Definition:
    $$RS = \frac{\text{EMA}(\text{Gain})}{\text{EMA}(\text{Loss})}, \quad \text{RSI} = 100 - \frac{100}{1 + RS}$$
    """
    if len(series) < 2:
        return pd.Series(50.0, index=series.index)

    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Use rolling mean with bfill consistent with existing model
    avg_gain = gain.rolling(window=window, min_periods=1).mean().bfill()
    avg_loss = loss.rolling(window=window, min_periods=1).mean().bfill()

    safe_loss = np.where(avg_loss == 0, 1e-9, avg_loss)
    rs = avg_gain / safe_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.bfill()


def calculate_macd(
    series: pd.Series,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
) -> pd.DataFrame:
    r"""
    Calculate Moving Average Convergence Divergence (MACD) and Signal Line.

    $$\text{MACD} = \text{EMA}_{\text{fast}} - \text{EMA}_{\text{slow}}$$
    $$\text{Signal} = \text{EMA}_{\text{signal}}(\text{MACD})$$
    """
    ema_fast = series.ewm(span=fast_window, adjust=False).mean().bfill()
    ema_slow = series.ewm(span=slow_window, adjust=False).mean().bfill()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean().bfill()
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {
            "MACD": macd_line,
            "Signal Line": signal_line,
            "MACD_Hist": histogram,
        },
        index=series.index,
    )


def calculate_bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Calculate Bollinger Bands (Middle, Upper, Lower)."""
    middle = series.rolling(window=window, min_periods=1).mean().bfill()
    std = series.rolling(window=window, min_periods=1).std().bfill()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    return pd.DataFrame(
        {"BB_Upper": upper, "BB_Middle": middle, "BB_Lower": lower},
        index=series.index,
    )


def apply_all_indicators(
    df: pd.DataFrame,
    price_col: str = "yt/underlying",
    params: TechnicalParams | None = None,
) -> pd.DataFrame:
    """Compute and append all technical indicators to DataFrame."""
    if df.empty or price_col not in df.columns:
        return df

    p = params or TechnicalParams()
    out = df.copy()
    prices = out[price_col]

    out["volatility"] = calculate_volatility(prices, window=p.volatility_window)
    out["moving_average_20"] = calculate_moving_average(prices, window=p.ma1_window)
    out["moving_average_50"] = calculate_moving_average(prices, window=p.ma2_window)
    out["moving_average_200"] = calculate_moving_average(prices, window=p.ma3_window)
    out["RSI"] = calculate_rsi(prices, window=p.rsi_window)

    macd_df = calculate_macd(
        prices,
        fast_window=p.ema_fast_window,
        slow_window=p.ema_slow_window,
        signal_window=p.macd_signal_window,
    )
    out["MACD"] = macd_df["MACD"]
    out["Signal Line"] = macd_df["Signal Line"]

    return out
