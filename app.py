"""Streamlit Web Application Entrypoint for Pendle Yield Token Analytics."""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to sys.path if not installed as package
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import streamlit as st

from yt_token.analytics import enrich_market_dataframe
from yt_token.client import (
    PendleApiClient,
    UnsupportedNetworkError,
    fetch_assets_data,
    find_valid_assets,
    is_valid_address,
)
from yt_token.ui.components import render_analysis_tabs, render_header, render_metric_cards
from yt_token.ui.sidebar import render_sidebar


def main() -> None:
    """Main Streamlit application lifecycle."""
    st.set_page_config(
        page_title="Pendle Yield Token Analytics",
        page_icon="🪙",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Render Sidebar & Gather Parameters
    state = render_sidebar()
    if not state:
        st.stop()

    # 2. Input Validation
    if not is_valid_address(state.market_contract) or not is_valid_address(state.yt_contract):
        st.error("Please provide valid 42-character EVM contract addresses (0x...) in the sidebar.")
        st.stop()

    # 3. Instantiate Client & Fetch Asset Metadata
    try:
        client = PendleApiClient(network=state.network)
    except UnsupportedNetworkError as e:
        st.error(str(e))
        st.stop()

    assets_url = client.get_assets_url()
    with st.spinner("Fetching market metadata from Pendle Finance..."):
        raw_assets = fetch_assets_data(assets_url, _session=client.session)

    valid_assets = find_valid_assets(raw_assets, "YT", "expiry", state.yt_contract)
    if not valid_assets:
        st.error(f"No valid Yield Token found matching contract `{state.yt_contract}` on {state.network.title()}.")
        st.info("💡 Try selecting one of the verified market presets in the sidebar.")
        st.stop()

    symbol = valid_assets[0].get("symbol", "YT-Token")
    maturity_str = valid_assets[0].get("expiry", "")
    try:
        maturity_time = datetime.fromisoformat(maturity_str.replace("Z", "+00:00"))
        if maturity_time.tzinfo is None:
            maturity_time = maturity_time.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        st.error(f"Failed to parse asset maturity timestamp: `{maturity_str}`")
        st.stop()

    # 4. Fetch Historical APY & OHLCV Timeseries
    now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    with st.spinner(f"Loading historical market time series for {symbol}..."):
        df_apy = client.fetch_market_apy(state.market_contract, state.start_time_str, now_utc_str)
        df_ohlcv = client.fetch_yt_ohlcv(state.yt_contract, state.start_time_str, now_utc_str)

    if df_apy.empty:
        st.error("No historical APY data available for this market.")
        st.info("Please verify the Market Contract address and ensure the Start Time is within the pool's lifetime.")
        st.stop()

    # 5. Enrich Quantitative Model Data
    df_enriched, implied_apy_avg, h_range, fair_curve = enrich_market_dataframe(
        df_apy=df_apy,
        df_ohlcv=df_ohlcv,
        maturity_time=maturity_time,
        params=state.quant_params,
    )

    if df_enriched.empty:
        st.error("Unable to calculate quantitative pricing model on empty data.")
        st.stop()

    # 6. Render Dashboard Components
    render_header(symbol=symbol, network=state.network, maturity_time=maturity_time)
    render_metric_cards(df=df_enriched, implied_apy_avg=implied_apy_avg, maturity_time=maturity_time)
    render_analysis_tabs(
        df=df_enriched,
        implied_apy_average=implied_apy_avg,
        h_range=h_range,
        fair_value_curve=fair_curve,
        symbol=symbol,
        maturity_time=maturity_time,
        state=state,
    )


if __name__ == "__main__":
    main()
