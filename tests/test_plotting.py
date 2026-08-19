"""Unit tests for Plotly visualization generators and annotations."""

from datetime import datetime

import numpy as np
import plotly.graph_objects as go

from yt_token.plotting import (
    add_purchase_time_annotation,
    plot_fair_value_comparison,
    plot_price_and_indicators,
    plot_volume_weighted_points,
    plot_yield_spread,
)


def test_add_purchase_time_annotation():
    fig = go.Figure()
    x_val = datetime(2024, 7, 25, 23, 0, 0)
    y_val = 100.5

    add_purchase_time_annotation(fig, x_val, y_val, text="Purchase Point")

    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0].x0 == x_val
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Purchase Point"


def test_plot_price_and_indicators(sample_ohlcv_df):
    df = sample_ohlcv_df.copy()
    df["yt/underlying"] = df["Close"]
    df["volatility"] = 0.01
    df["RSI"] = 55.0
    df["MACD"] = 0.001
    df["Signal Line"] = 0.0005

    fig = plot_price_and_indicators(
        df,
        symbol="YT-TEST",
        network="ethereum",
        dark_mode=True,
        show_volatility=True,
        show_mas=True,
        show_rsi=True,
        show_macd=True,
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2


def test_plot_fair_value_comparison(sample_ohlcv_df):
    df = sample_ohlcv_df.copy()
    df["yt/underlying"] = df["Close"]
    df["points"] = 1000.0
    df["difference"] = 0.01
    h_range = df["Time"]
    fair_curve = np.linspace(0.05, 0.0, len(df))

    fig = plot_fair_value_comparison(
        df,
        h_range,
        fair_curve,
        symbol="YT-TEST",
        network="ethereum",
        show_difference=True,
        dark_mode=True,
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 3


def test_plot_yield_spread(sample_apy_df):
    df = sample_apy_df.copy()
    df["Time"] = df["timestamp"]
    df["long_yield_apy"] = 0.15

    fig = plot_yield_spread(df, symbol="YT-TEST", network="ethereum", dark_mode=False)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_plot_volume_weighted_points(sample_ohlcv_df):
    df = sample_ohlcv_df.copy()
    df["weighted_points"] = 50.0

    fig = plot_volume_weighted_points(df, symbol="YT-TEST", network="ethereum")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
