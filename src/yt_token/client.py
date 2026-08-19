"""Robust HTTP client for interacting with Pendle Finance v2 APIs."""

import re
from io import StringIO
from typing import Any

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from yt_token.config import (
    API_BASE_V1,
    API_BASE_V3,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
    NETWORK_IDS,
)
from yt_token.models import Asset, DiscoveredMarket


class PendleApiError(Exception):
    """Base exception for Pendle API failures."""

    pass


class UnsupportedNetworkError(PendleApiError):
    """Raised when an unsupported EVM network is requested."""

    pass


def is_valid_address(address: Any) -> bool:
    """Validate whether the provided string is a valid EVM contract address (0x followed by 40 hex chars)."""
    if not isinstance(address, str):
        return False
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", address.strip()))


def create_resilient_session(
    total_retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: list[int] | None = None,
) -> requests.Session:
    """Create a configured requests.Session with connection pooling and exponential backoff retries."""
    session = requests.Session()
    status_list = status_forcelist or [429, 500, 502, 503, 504]
    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_list,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Shared default HTTP headers
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "application/json",
}


@st.cache_data(ttl=600, show_spinner=False)
def fetch_markets_data(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    _session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch active markets from Pendle API with Streamlit data caching."""
    if not url:
        return []
    s = _session or create_resilient_session()
    params: dict[str, str | int] = {"limit": 100, "is_active": "true"}
    try:
        response = s.get(url, headers=DEFAULT_HEADERS, params=params, timeout=timeout)
        if response.status_code == 200:
            json_data = response.json()
            if isinstance(json_data, dict):
                return json_data.get("results", [])
            elif isinstance(json_data, list):
                return json_data
    except Exception:
        pass
    return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_assets_data(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    _session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch all market assets from Pendle API with Streamlit data caching."""
    if not url:
        return []
    s = _session or create_resilient_session()
    response = s.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    if response.status_code == 200:
        json_data = response.json()
        if isinstance(json_data, list):
            return json_data
        elif isinstance(json_data, dict):
            return json_data.get("results", [])
    return []


def find_valid_assets(
    data: list[dict[str, Any]],
    base_type: str,
    expiry_key: str,
    address: str,
) -> list[dict[str, Any]]:
    """Search and filter asset listings matching base type, address, and expiry key presence."""
    if not data or not address:
        return []
    target_addr = address.lower().strip()
    return [
        item
        for item in data
        if item.get("baseType", "").upper() == base_type.upper()
        and str(item.get("address", "")).lower() == target_addr
        and expiry_key in item
    ]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_yteth_ohlcv_data(
    url: str,
    start_time_str: str,
    end_time_str: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    _session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV candlestick time series for a Yield Token and parse into a typed DataFrame."""
    columns = ["Time", "Open", "High", "Low", "Close", "Volume"]
    if not url:
        return pd.DataFrame(columns=columns)

    s = _session or create_resilient_session()
    params = {
        "time_frame": "hour",
        "timestamp_start": start_time_str,
        "timestamp_end": end_time_str,
    }
    response = s.get(url, headers=DEFAULT_HEADERS, params=params, timeout=timeout)
    if response.status_code != 200:
        return pd.DataFrame(columns=columns)

    json_data = response.json()
    if isinstance(json_data, dict):
        results = json_data.get("results", [])
    elif isinstance(json_data, list):
        results = json_data
    else:
        results = []

    if not results:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(results)
    df["Time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    if "volume" not in df.columns:
        df["Volume"] = 0.0
    else:
        df["Volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)

    renamed = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
    )
    for col in ["Open", "High", "Low", "Close"]:
        if col in renamed.columns:
            renamed[col] = pd.to_numeric(renamed[col], errors="coerce").fillna(0.0)

    return renamed[columns]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_apy_data(
    url: str,
    start_time_str: str,
    end_time_str: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    _session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch historical APY data (implied and underlying) for a market and parse into a DataFrame."""
    if not url:
        return pd.DataFrame()

    s = _session or create_resilient_session()
    params = {
        "time_frame": "hour",
        "timestamp_start": start_time_str,
        "timestamp_end": end_time_str,
    }
    response = s.get(url, headers=DEFAULT_HEADERS, params=params, timeout=timeout)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and "results" in data:
            csv_data = data["results"]
            if not csv_data or not isinstance(csv_data, str) or not csv_data.strip():
                return pd.DataFrame()
            df = pd.read_csv(StringIO(csv_data))
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
            for col in ["impliedApy", "underlyingApy"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            return df
        else:
            if hasattr(st, "error"):
                st.error("No results found in the API response")
            return pd.DataFrame()
    else:
        if hasattr(st, "error"):
            st.error(f"Failed to retrieve data with status code: {response.status_code}")
        return pd.DataFrame()


class PendleApiClient:
    """High-level client managing requests to Pendle Finance v2 APIs."""

    def __init__(self, network: str = "ethereum", session: requests.Session | None = None) -> None:
        self.network = network.lower().strip()
        self.network_id = NETWORK_IDS.get(self.network)
        if self.network_id is None:
            raise UnsupportedNetworkError(
                f"Network '{network}' is not supported. Choose from: {list(NETWORK_IDS.keys())}"
            )
        self.session = session or create_resilient_session()

    def get_markets_url(self) -> str:
        return f"{API_BASE_V1}{self.network_id}/markets"

    def get_assets_url(self) -> str:
        return f"{API_BASE_V1}{self.network_id}/assets/all"

    def get_market_apy_url(self, market_address: str) -> str:
        return f"{API_BASE_V1}{self.network_id}/markets/{market_address.lower()}/apy-history-1ma"

    def get_yt_ohlcv_url(self, yt_address: str) -> str:
        return f"{API_BASE_V3}{self.network_id}/prices/{yt_address.lower()}/ohlcv"

    def fetch_active_markets(self) -> list[DiscoveredMarket]:
        """Fetch and parse live active markets for the configured network sorted by liquidity."""
        url = self.get_markets_url()
        raw_items = fetch_markets_data(url, _session=self.session)
        discovered: list[DiscoveredMarket] = []
        for item in raw_items:
            m_addr = str(item.get("address") or "").lower()
            yt_info = item.get("yt", {})
            yt_addr = (str(yt_info.get("address") or "") if isinstance(yt_info, dict) else "").lower()
            if not m_addr or not yt_addr:
                continue
            name = item.get("proName") or item.get("name") or item.get("symbol") or "Market Pool"
            liq = item.get("liquidity", {})
            liq_usd = float(liq.get("usd", 0.0)) if isinstance(liq, dict) else 0.0
            vol = item.get("tradingVolume", {})
            vol_usd = float(vol.get("usd", 0.0)) if isinstance(vol, dict) else 0.0
            discovered.append(
                DiscoveredMarket(
                    name=name,
                    symbol=item.get("symbol", ""),
                    network=self.network,
                    market_address=m_addr,
                    yt_address=yt_addr,
                    expiry=item.get("expiry", ""),
                    liquidity_usd=liq_usd,
                    trading_volume_usd=vol_usd,
                    implied_apy=float(item.get("impliedApy", 0.0) or 0.0),
                    underlying_apy=float(item.get("underlyingApy", 0.0) or 0.0),
                )
            )
        discovered.sort(key=lambda m: m.liquidity_usd, reverse=True)
        return discovered

    def fetch_all_assets(self) -> list[Asset]:
        url = self.get_assets_url()
        raw_items = fetch_assets_data(url, _session=self.session)
        return [Asset.from_dict(item) for item in raw_items]

    def fetch_market_apy(self, market_address: str, start_time_str: str, end_time_str: str) -> pd.DataFrame:
        url = self.get_market_apy_url(market_address)
        return fetch_apy_data(url, start_time_str, end_time_str, _session=self.session)

    def fetch_yt_ohlcv(self, yt_address: str, start_time_str: str, end_time_str: str) -> pd.DataFrame:
        url = self.get_yt_ohlcv_url(yt_address)
        return fetch_yteth_ohlcv_data(url, start_time_str, end_time_str, _session=self.session)
