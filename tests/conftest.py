"""Pytest configuration and shared fixtures for YT_Token test suite."""

from typing import Any

import pandas as pd
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test run."""
    if hasattr(st, "cache_data"):
        st.cache_data.clear()
    yield
    if hasattr(st, "cache_data"):
        st.cache_data.clear()


@pytest.fixture
def sample_assets_raw() -> list[dict[str, Any]]:
    """Sample raw asset payload returned by Pendle API."""
    return [
        {
            "baseType": "YT",
            "address": "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            "expiry": "2024-12-31T00:00:00Z",
            "symbol": "YT-USDe-31DEC2024",
            "name": "Yield Token USDe",
            "decimals": 18,
        },
        {
            "baseType": "PT",
            "address": "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            "expiry": "2024-12-31T00:00:00Z",
            "symbol": "PT-USDe-31DEC2024",
            "name": "Principal Token USDe",
            "decimals": 18,
        },
        {
            "baseType": "YT",
            "address": "0x25a95610e206013a7c644ca70ad255b6eb2690ff",
            "expiry": "2025-06-26T00:00:00Z",
            "symbol": "YT-eETH-26JUN2025",
            "name": "Yield Token eETH",
            "decimals": 18,
        },
    ]


@pytest.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """Sample OHLCV DataFrame."""
    dates = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "Time": dates,
            "Open": [0.05, 0.051, 0.052, 0.049, 0.048, 0.050, 0.053, 0.052, 0.051, 0.050],
            "High": [0.052, 0.053, 0.054, 0.051, 0.050, 0.052, 0.055, 0.054, 0.053, 0.052],
            "Low": [0.049, 0.050, 0.051, 0.048, 0.047, 0.049, 0.051, 0.050, 0.049, 0.048],
            "Close": [0.051, 0.052, 0.049, 0.048, 0.050, 0.053, 0.052, 0.051, 0.050, 0.051],
            "Volume": [100.0, 150.0, 200.0, 120.0, 80.0, 250.0, 300.0, 190.0, 140.0, 220.0],
        }
    )


@pytest.fixture
def sample_apy_df() -> pd.DataFrame:
    """Sample historical APY DataFrame."""
    dates = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": dates,
            "impliedApy": [0.05, 0.052, 0.051, 0.049, 0.048, 0.053, 0.055, 0.054, 0.052, 0.050],
            "underlyingApy": [0.08, 0.081, 0.080, 0.079, 0.078, 0.082, 0.085, 0.084, 0.082, 0.080],
        }
    )
