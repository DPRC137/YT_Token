"""
Legacy entrypoint and compatibility layer for YT_Token.
Delegates to the modern src.yt_token package while preserving 100% backward compatibility
for existing tests, external imports, and legacy scripts.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Ensure src/ is importable
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from yt_token.client import (
    fetch_apy_data as _fetch_apy_data,
)
from yt_token.client import (
    fetch_yteth_ohlcv_data as _fetch_yteth_ohlcv_data,
)
from yt_token.client import (
    find_valid_assets as _find_valid_assets,
)
from yt_token.client import (
    is_valid_address as _is_valid_address,
)
from yt_token.plotting import add_purchase_time_annotation as _add_purchase_time_annotation

# Re-export legacy constants and globals
network_ids: dict[str, str] = {
    "arbitrum": "/42161",
    "ethereum": "/1",
    "mantle": "/5000",
}
headers: dict[str, str] = {
    "User-Agent": "Mozilla/5.0",
}

# Set up the session with retries
session = requests.session()
retry = requests.packages.urllib3.util.retry.Retry(total=3, backoff_factor=1)
session.mount("http://", requests.adapters.HTTPAdapter(max_retries=retry))
session.mount("https://", requests.adapters.HTTPAdapter(max_retries=retry))


def is_valid_address(address: Any) -> bool:
    """Validates if the provided string is a valid EVM contract address (0x followed by 40 hex chars)."""
    return _is_valid_address(address)


def find_valid_assets(
    data: list[dict[str, Any]],
    base_type: str,
    expiry_key: str,
    address: str,
) -> list[dict[str, Any]]:
    """Search and filter asset listings matching base type, address, and expiry key presence."""
    return _find_valid_assets(data, base_type, expiry_key, address)


def add_purchase_time_annotation(
    fig: go.Figure,
    x_value: Any,
    y_value: Any,
    text: str = "YT Purchase Time",
) -> None:
    """Add a vertical line and annotation to a Plotly figure."""
    _add_purchase_time_annotation(fig, x_value, y_value, text)


@st.cache_data
def fetch_assets_data(url: str, timeout: int = 10, _session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Fetch assets metadata with Streamlit caching."""
    s = _session or session
    response = s.get(url, headers=headers, timeout=timeout)
    if hasattr(response, "json"):
        return response.json()
    return []


@st.cache_data
def fetch_yteth_ohlcv_data(
    url: str,
    start_time_str: str,
    end_time_str: str,
    timeout: int = 10,
    _session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV candlestick time series for Yield Token with Streamlit caching."""
    return _fetch_yteth_ohlcv_data(url, start_time_str, end_time_str, timeout=timeout, _session=_session or session)


@st.cache_data
def fetch_apy_data(
    url: str,
    start_time_str: str,
    end_time_str: str,
    timeout: int = 10,
    _session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch historical APY data with Streamlit caching."""
    return _fetch_apy_data(url, start_time_str, end_time_str, timeout=timeout, _session=_session or session)


class Main:
    """Legacy Main class for Data Acquisition and Analysis."""

    def __init__(
        self,
        market_contract: str,
        yt_contract: str,
        start_time_str: str,
        network: str,
    ) -> None:
        self.session = session
        self.market_contract = market_contract
        self.yt_contract = yt_contract
        self.start_time_str = start_time_str
        self.end_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        self.interval = "1h"
        self.url_apy: str | None = None
        self.url_ohlcv_yteth: str | None = None

        if not is_valid_address(self.market_contract):
            if hasattr(st, "error"):
                st.error("Invalid market contract address format.")
            return

        if not is_valid_address(self.yt_contract):
            if hasattr(st, "error"):
                st.error("Invalid yield token contract address format.")
            return

        network_id = network_ids.get(network.lower())
        if network_id is not None:
            self.url_apy = (
                f"https://api-v2.pendle.finance/core/v1{network_id}/markets/{self.market_contract}/apy-history-1ma"
            )
            self.url_ohlcv_yteth = f"https://api-v2.pendle.finance/core/v3{network_id}/prices/{self.yt_contract}/ohlcv"
        else:
            if hasattr(st, "error"):
                st.error("Unsupported network type")

    def fetch_yteth_ohlcv(self) -> pd.DataFrame:
        if not self.url_ohlcv_yteth:
            return pd.DataFrame(columns=["Time", "Open", "High", "Low", "Close", "Volume"])
        return fetch_yteth_ohlcv_data(
            self.url_ohlcv_yteth,
            self.start_time_str,
            self.end_time_str,
            timeout=10,
            _session=self.session,
        )

    def fetch_apy(self) -> pd.DataFrame:
        if not self.url_apy:
            if hasattr(st, "error"):
                st.error("Unsupported network type")
            return pd.DataFrame()
        return fetch_apy_data(
            self.url_apy,
            self.start_time_str,
            self.end_time_str,
            timeout=10,
            _session=self.session,
        )

    def run(self) -> pd.DataFrame:
        df = self.fetch_apy()
        ohlcv = self.fetch_yteth_ohlcv()
        if not df.empty and not ohlcv.empty and "Volume" in ohlcv.columns:
            df["volume"] = ohlcv["Volume"]
            return df
        elif not df.empty:
            df["volume"] = 1.0
            return df
        else:
            if hasattr(st, "error"):
                st.error("No data to display.")
            return pd.DataFrame()


# Script-level execution when imported/executed under Streamlit
try:
    if hasattr(st, "selectbox"):
        network_val = st.selectbox("Select Network", ["ethereum", "arbitrum", "mantle"], index=0)
        net_id = network_ids.get(str(network_val).lower())
        if net_id is not None:
            url_val = f"https://api-v2.pendle.finance/core/v1{net_id}/assets/all"
        else:
            st.error("Unsupported network type")
            st.stop()

        market_contract_val = st.text_input("Market Contract Address", "0x00b321d89a8c36b3929f20b7955080baed706d1b")
        yt_contract_val = st.text_input("Yield Token Contract Address", "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d")
        start_time_val = st.text_input("Start Time (UTC)", "2023-01-01 00:00:00")
        underlying_amount_val = st.number_input("Underlying Amount", 1)
        points_val = st.number_input("Points per Hour per Underlying", 0.04)
        multiplier_val = st.number_input("Pendle YT Multiplier", 5)
        dark_mode_val = st.checkbox("Dark Mode")

        data_val = fetch_assets_data(url_val, timeout=10)
        valid_assets_val = find_valid_assets(data_val, "YT", "expiry", yt_contract_val)
        if not valid_assets_val:
            st.error("No valid assets found.")
            st.stop()
except Exception as _e:
    if "st.stop called" in str(_e) or type(_e).__name__ == "StopException":
        raise
