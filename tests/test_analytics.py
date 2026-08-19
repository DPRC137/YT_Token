"""Unit tests for quantitative pricing math, fair value curves, and simulations."""

from datetime import datetime, timezone

import pytest

from yt_token.analytics import (
    analyze_historical_purchase,
    calculate_hours_to_maturity,
    calculate_points_earned,
    calculate_yt_price,
    enrich_market_dataframe,
    simulate_limit_order,
)
from yt_token.config import QuantitativeParams


def test_calculate_hours_to_maturity():
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    maturity = datetime(2024, 1, 10, 0, 0, tzinfo=timezone.utc)
    hours = calculate_hours_to_maturity(t0, maturity)
    assert hours == 9 * 24.0


def test_calculate_yt_price():
    # When hours to maturity = 8760 (1 year), and implied APY = 10% (0.10), YT price = (1.10)^1 - 1 = 0.10
    price_1y = calculate_yt_price(0.10, 8760.0, annual_hours=8760.0)
    assert pytest.approx(price_1y, rel=1e-5) == 0.10

    # Half year: (1.10)^0.5 - 1
    price_half_y = calculate_yt_price(0.10, 4380.0, annual_hours=8760.0)
    assert pytest.approx(price_half_y, rel=1e-5) == (1.10**0.5 - 1.0)


def test_calculate_points_earned():
    yt_price = 0.05
    time_diff_hours = 1000.0
    points_rate = 0.04
    underlying = 1.0
    multiplier = 5.0

    # leverage = 1 / 0.05 * 5 = 100x
    # points = 100 * 1000 * 0.04 * 1.0 = 4000
    points = calculate_points_earned(yt_price, time_diff_hours, points_rate, underlying, multiplier)
    assert pytest.approx(points, rel=1e-5) == 4000.0


def test_enrich_market_dataframe(sample_apy_df, sample_ohlcv_df):
    maturity = datetime(2024, 12, 31, 0, 0, tzinfo=timezone.utc)
    df_en, implied_avg, h_range, fair_curve = enrich_market_dataframe(
        sample_apy_df,
        sample_ohlcv_df,
        maturity,
        QuantitativeParams(),
    )
    assert not df_en.empty
    assert "yt/underlying" in df_en.columns
    assert "long_yield_apy" in df_en.columns
    assert "points" in df_en.columns
    assert "fair" in df_en.columns
    assert "difference" in df_en.columns
    assert implied_avg > 0


def test_analyze_historical_purchase(sample_apy_df, sample_ohlcv_df):
    maturity = datetime(2024, 12, 31, 0, 0, tzinfo=timezone.utc)
    df_en, _, _, _ = enrich_market_dataframe(sample_apy_df, sample_ohlcv_df, maturity)

    purchase_time = datetime(2024, 1, 1, 3, 30, tzinfo=timezone.utc)
    result = analyze_historical_purchase(df_en, purchase_time, maturity)

    assert result is not None
    assert result.yt_price > 0
    assert result.leverage > 0
    assert result.points_at_maturity > 0
    assert 0.0 <= result.percentile_outperformed <= 100.0


def test_simulate_limit_order(sample_apy_df, sample_ohlcv_df):
    maturity = datetime(2024, 12, 31, 0, 0, tzinfo=timezone.utc)
    df_en, _, _, _ = enrich_market_dataframe(sample_apy_df, sample_ohlcv_df, maturity)

    target_time = datetime(2024, 1, 5, 0, 0, tzinfo=timezone.utc)
    sim = simulate_limit_order(df_en, target_time, target_implied_apy=0.04, maturity_time=maturity)

    assert sim is not None
    assert sim.simulated_price > 0
    assert sim.simulated_points > 0
    assert sim.leverage > 0
