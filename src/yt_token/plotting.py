"""Interactive financial visualization engine built on Plotly."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def add_purchase_time_annotation(
    fig: go.Figure,
    x_value: Any,
    y_value: Any,
    text: str = "YT Purchase Time",
) -> None:
    """Add a vertical marker and labeled annotation for a historical purchase point."""
    fig.add_vline(x=x_value, line_width=3, line_dash="dash", line_color="green")
    fig.add_annotation(
        x=x_value,
        y=y_value,
        text=text,
        showarrow=True,
        arrowhead=1,
        ax=20,
        ay=-30,
    )


def plot_price_and_indicators(
    df: pd.DataFrame,
    symbol: str,
    network: str,
    dark_mode: bool = True,
    show_volatility: bool = True,
    show_mas: bool = True,
    show_rsi: bool = False,
    show_macd: bool = False,
    annotation_dt: datetime | None = None,
) -> go.Figure:
    """Build multi-axis interactive chart for YT Price and Technical Indicators."""
    template = "plotly_dark" if dark_mode else "plotly_white"
    fig = go.Figure()

    # Base YT Price
    fig.add_trace(
        go.Scatter(
            x=df["Time"],
            y=df["yt/underlying"],
            mode="lines",
            name="YT Price",
            line=dict(color="#00B0FF", width=2.2),
            yaxis="y",
        )
    )

    if show_mas:
        if "moving_average_20" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["Time"],
                    y=df["moving_average_20"],
                    mode="lines",
                    name="20-day MA",
                    line=dict(color="#FFD600", width=1.2),
                )
            )
        if "moving_average_50" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["Time"],
                    y=df["moving_average_50"],
                    mode="lines",
                    name="50-day MA",
                    line=dict(color="#FF9100", width=1.2),
                )
            )
        if "moving_average_200" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["Time"],
                    y=df["moving_average_200"],
                    mode="lines",
                    name="200-day MA",
                    line=dict(color="#FF3D00", width=1.2),
                )
            )

    if show_volatility and "volatility" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["volatility"],
                mode="lines",
                name="Volatility",
                line=dict(color="#E040FB", width=1.2, dash="dot"),
                yaxis="y2",
            )
        )

    if show_rsi and "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["RSI"],
                mode="lines",
                name="RSI",
                line=dict(color="#00E5FF", width=1.2),
                yaxis="y3",
            )
        )

    if show_macd and "MACD" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["MACD"],
                mode="lines",
                name="MACD",
                line=dict(color="#76FF03", width=1.2),
                yaxis="y4",
            )
        )
        if "Signal Line" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["Time"],
                    y=df["Signal Line"],
                    mode="lines",
                    name="Signal Line",
                    line=dict(color="#FF1744", width=1.2, dash="dash"),
                    yaxis="y4",
                )
            )

    fig.update_layout(
        title=f"<b>{symbol}</b> on {network} YT/Underlying asset",
        xaxis_title="Time",
        yaxis_title="YT Price (per Underlying)",
        template=template,
        yaxis2=dict(title="Volatility", overlaying="y", side="right", position=0.85) if show_volatility else None,
        yaxis3=dict(title="RSI", overlaying="y", side="right", position=0.90) if show_rsi else None,
        yaxis4=dict(title="MACD", overlaying="y", side="right", position=0.95) if show_macd else None,
    )

    if annotation_dt and not df.empty:
        add_purchase_time_annotation(fig, annotation_dt, float(df["yt/underlying"].max()))

    return fig


def plot_fair_value_comparison(
    df: pd.DataFrame,
    h_range: pd.DatetimeIndex,
    fair_value_curve: np.ndarray | pd.Series,
    symbol: str,
    network: str,
    underlying_amount: float = 1.0,
    show_difference: bool = True,
    dark_mode: bool = True,
    annotation_dt: datetime | None = None,
) -> go.Figure:
    """Build Valuation & Fair Value Decay vs Market Price comparison chart."""
    template = "plotly_dark" if dark_mode else "plotly_white"
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time"],
            y=df["yt/underlying"],
            mode="lines",
            name="YT Price",
            line=dict(color="#00E5FF", width=2.5),
            yaxis="y",
        )
    )

    if "points" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["points"],
                mode="lines",
                name="Points Earned",
                line=dict(color="#00E676", width=1.8),
                yaxis="y2",
            )
        )

    if show_difference and "difference" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["difference"],
                mode="lines",
                name="Difference between Fair and Market Price",
                line=dict(color="#FF5252", width=1.5, dash="dash"),
                yaxis="y3",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=h_range,
            y=fair_value_curve,
            mode="lines",
            name="Fair Value Curve of YT",
            line=dict(color="yellow", dash="dot", width=3),
            yaxis="y",
        )
    )

    fig.update_layout(
        title=f"<b>{symbol}</b> on {network} [{underlying_amount} underlying coin] | BUY YT WHEN THE YT Price IS UNDER THE FAIR VALUE CURVE TO MAXIMIZE POINTS EARNED",
        xaxis_title="Certain Time of Purchasing YT",
        yaxis=dict(title="YT Price", side="left"),
        yaxis2=dict(title="Points Earned", overlaying="y", side="right"),
        yaxis3=dict(title="Difference", overlaying="y", side="right", position=0.92) if show_difference else None,
        template=template,
    )

    if annotation_dt and not df.empty:
        add_purchase_time_annotation(fig, annotation_dt, float(df["yt/underlying"].max()) * 0.5)

    return fig


def plot_yield_spread(
    df: pd.DataFrame,
    symbol: str,
    network: str,
    dark_mode: bool = True,
    annotation_dt: datetime | None = None,
) -> go.Figure:
    """Build Long Yield APY vs Implied APY comparison chart."""
    template = "plotly_dark" if dark_mode else "plotly_white"
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time"],
            y=df["long_yield_apy"],
            mode="lines",
            name="Long Yield APY",
            line=dict(color="#76FF03", width=2),
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time"],
            y=df["impliedApy"],
            mode="lines",
            name="Implied APY",
            line=dict(color="#FF9100", width=2),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=f"<b>{symbol}</b> on {network} | Long Yield APY vs. Implied APY",
        xaxis_title="Certain Time of Purchasing YT",
        yaxis=dict(title="Long Yield APY", side="left"),
        yaxis2=dict(title="Implied APY", overlaying="y", side="right"),
        template=template,
    )

    if annotation_dt and not df.empty:
        add_purchase_time_annotation(fig, annotation_dt, float(df["long_yield_apy"].max()))

    return fig


def plot_volume_weighted_points(
    df: pd.DataFrame,
    symbol: str,
    network: str,
    dark_mode: bool = True,
    annotation_dt: datetime | None = None,
) -> go.Figure:
    """Build Volume-Weighted Points Distribution chart."""
    template = "plotly_dark" if dark_mode else "plotly_white"
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time"],
            y=df["weighted_points"],
            mode="lines",
            name="Weighted Points",
            line=dict(color="#E040FB", width=2),
        )
    )

    fig.update_layout(
        title=f"<b>{symbol}</b> on {network} | Weighted Points (by Volume) Over Time",
        xaxis_title="Time",
        yaxis_title="Weighted Points",
        template=template,
    )

    if annotation_dt and not df.empty:
        add_purchase_time_annotation(fig, annotation_dt, float(df["weighted_points"].max()))

    return fig
