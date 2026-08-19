"""Unit tests for technical analysis indicators (RSI, MACD, Moving Averages, Volatility)."""

import numpy as np
import pandas as pd
import pytest

from yt_token.indicators import (
    apply_all_indicators,
    calculate_bollinger_bands,
    calculate_macd,
    calculate_moving_average,
    calculate_rsi,
    calculate_volatility,
)


def test_calculate_moving_average():
    s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    ma = calculate_moving_average(s, window=3)
    assert len(ma) == 5
    assert ma.iloc[2] == pytest.approx(20.0)  # (10+20+30)/3
    assert ma.iloc[4] == pytest.approx(40.0)  # (30+40+50)/3


def test_calculate_rsi():
    # Steadily increasing prices -> high RSI
    s_up = pd.Series(range(1, 100), dtype=float)
    rsi_up = calculate_rsi(s_up, window=14)
    assert not rsi_up.isna().any()
    assert rsi_up.iloc[-1] > 90.0

    # Steadily decreasing prices -> low RSI
    s_down = pd.Series(range(100, 1, -1), dtype=float)
    rsi_down = calculate_rsi(s_down, window=14)
    assert not rsi_down.isna().any()
    assert rsi_down.iloc[-1] < 10.0


def test_calculate_macd():
    s = pd.Series(np.linspace(10, 50, 50))
    macd_df = calculate_macd(s, fast_window=12, slow_window=26, signal_window=9)
    assert "MACD" in macd_df.columns
    assert "Signal Line" in macd_df.columns
    assert "MACD_Hist" in macd_df.columns
    assert len(macd_df) == 50


def test_calculate_volatility():
    s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
    vol = calculate_volatility(s, window=3)
    assert vol.iloc[-1] == pytest.approx(0.0)

    s_noisy = pd.Series([10.0, 20.0, 5.0, 30.0, 15.0])
    vol_noisy = calculate_volatility(s_noisy, window=3)
    assert vol_noisy.iloc[-1] > 0.0


def test_calculate_bollinger_bands():
    s = pd.Series(np.random.normal(100, 5, 50))
    bb = calculate_bollinger_bands(s, window=20, num_std=2.0)
    assert (bb["BB_Upper"] >= bb["BB_Middle"]).all()
    assert (bb["BB_Middle"] >= bb["BB_Lower"]).all()


def test_apply_all_indicators(sample_ohlcv_df):
    df_ind = apply_all_indicators(sample_ohlcv_df, price_col="Close")
    assert "volatility" in df_ind.columns
    assert "moving_average_20" in df_ind.columns
    assert "moving_average_50" in df_ind.columns
    assert "moving_average_200" in df_ind.columns
    assert "RSI" in df_ind.columns
    assert "MACD" in df_ind.columns
    assert "Signal Line" in df_ind.columns
