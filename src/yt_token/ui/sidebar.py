"""Streamlit sidebar input controls, dynamic market discovery, and parameter configuration."""

from dataclasses import dataclass
from datetime import datetime, timezone

import streamlit as st

from yt_token.client import PendleApiClient, is_valid_address
from yt_token.config import (
    MARKET_PRESETS,
    NETWORK_IDS,
    MarketPreset,
    QuantitativeParams,
    TechnicalParams,
)
from yt_token.models import DiscoveredMarket


@dataclass
class SidebarState:
    """Consolidated state payload from all user sidebar interactions."""

    network: str
    market_contract: str
    yt_contract: str
    start_time_str: str
    quant_params: QuantitativeParams
    tech_params: TechnicalParams
    dark_mode: bool

    # Selected Market Name
    selected_market_name: str

    # Simulation 1 (Historical Purchase)
    enable_analysis_1: bool
    yt_purchase_time_dt: datetime | None
    underlying_invest_amount: float

    # Simulation 2 (Limit Order)
    enable_analysis_2: bool
    limit_order_time_dt: datetime | None
    limit_order_implied_apy: float
    limit_order_invest_amount: float


def render_sidebar() -> SidebarState | None:
    """Render the sidebar UI components and return the configured state."""
    st.sidebar.markdown("## ⚙️ Market & Parameters")

    # 1. Network Selection
    network_list = list(NETWORK_IDS.keys())
    network = st.sidebar.selectbox("Network", network_list, index=0)

    # 2. Dynamic Market Discovery
    discovered_markets: list[DiscoveredMarket] = []
    try:
        client = PendleApiClient(network=network)
        discovered_markets = client.fetch_active_markets()
    except Exception:
        discovered_markets = []

    # Build options list
    custom_option = "⚙️ Custom Contract Address..."
    options: list[str] = []
    market_map: dict[str, DiscoveredMarket | MarketPreset] = {}

    if discovered_markets:
        for dm in discovered_markets[:30]:  # top 30 active pools by liquidity
            label = f"🔥 {dm.display_label}"
            options.append(label)
            market_map[label] = dm
    else:
        # Fallback to static presets matching selected network
        net_presets = [p for p in MARKET_PRESETS if p.network == network]
        for p in net_presets:
            label = f"📌 {p.name}"
            options.append(label)
            market_map[label] = p

    options.append(custom_option)

    selected_option = st.sidebar.selectbox(
        "Select Market Pool",
        options=options,
        index=0,
        help="Dynamically fetched from Pendle API, sorted by TVL/Liquidity.",
    )

    selected_market_name = "Custom"
    if selected_option == custom_option:
        market_contract = st.sidebar.text_input(
            "Market Contract Address",
            value="0x00b321d89a8c36b3929f20b7955080baed706d1b",
            help="EVM hex address of the Pendle v2 Market contract.",
        ).strip()

        yt_contract = st.sidebar.text_input(
            "Yield Token (YT) Address",
            value="0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            help="EVM hex address of the Pendle Yield Token (YT).",
        ).strip()
    else:
        m_item = market_map.get(selected_option)
        if isinstance(m_item, DiscoveredMarket):
            default_market = m_item.market_address
            default_yt = m_item.yt_address
            selected_market_name = m_item.name
        elif isinstance(m_item, MarketPreset):
            default_market = m_item.market_address
            default_yt = m_item.yt_address
            selected_market_name = m_item.name
        else:
            default_market = "0x00b321d89a8c36b3929f20b7955080baed706d1b"
            default_yt = "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d"

        # Show auto-populated addresses in a neat expander
        with st.sidebar.expander("🔍 Contract Addresses (Auto-Configured)", expanded=False):
            market_contract = st.text_input("Market Contract", value=default_market).strip()
            yt_contract = st.text_input("YT Contract", value=default_yt).strip()

    # Address validation warnings
    if not is_valid_address(market_contract):
        st.sidebar.error("❌ Invalid Market contract address format")
    if not is_valid_address(yt_contract):
        st.sidebar.error("❌ Invalid YT contract address format")

    start_time_input = st.sidebar.text_input("Start Time (UTC)", "2023-01-01 00:00:00")
    try:
        dt_obj = datetime.strptime(start_time_input.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        start_time_str = dt_obj.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except ValueError:
        st.sidebar.error("❌ Invalid Start Time format. Use YYYY-MM-DD HH:MM:SS")
        start_time_str = "2023-01-01T00:00:00.000Z"

    # 4. Quantitative & Farming Parameters
    with st.sidebar.expander("🌾 Point Farming & Quantitative Settings", expanded=False):
        underlying_amount = st.number_input("Underlying Benchmark Amount", min_value=0.01, value=1.0, step=0.1)
        points_per_hour = st.number_input(
            "Points Rate per Hour (per Underlying)", min_value=0.001, value=0.04, step=0.01, format="%.4f"
        )
        yt_multiplier = st.number_input("Pendle YT Point Multiplier", min_value=1.0, value=5.0, step=1.0)
        quant_params = QuantitativeParams(
            underlying_amount=float(underlying_amount),
            points_per_hour_per_underlying=float(points_per_hour),
            pendle_yt_multiplier=float(yt_multiplier),
        )

    # 5. Technical Analysis Hyperparameters
    with st.sidebar.expander("📈 Technical Indicators Configuration", expanded=False):
        vol_win = st.number_input("Volatility Window", min_value=2, value=48)
        ma1_win = st.number_input("Fast Moving Average (MA 1)", min_value=1, value=24)
        ma2_win = st.number_input("Medium Moving Average (MA 2)", min_value=1, value=72)
        ma3_win = st.number_input("Slow Moving Average (MA 3)", min_value=1, value=216)
        rsi_win = st.number_input("RSI Window", min_value=2, value=72)
        ema_fast = st.number_input("MACD Fast Window", min_value=1, value=12)
        ema_slow = st.number_input("MACD Slow Window", min_value=1, value=26)
        macd_sig = st.number_input("MACD Signal Window", min_value=1, value=9)

        tech_params = TechnicalParams(
            volatility_window=int(vol_win),
            ma1_window=int(ma1_win),
            ma2_window=int(ma2_win),
            ma3_window=int(ma3_win),
            rsi_window=int(rsi_win),
            ema_fast_window=int(ema_fast),
            ema_slow_window=int(ema_slow),
            macd_signal_window=int(macd_sig),
        )

    # 6. Scenario Simulators
    with st.sidebar.expander("🎯 Scenario & Investment Analysis", expanded=False):
        enable_analysis_1 = st.checkbox("Enable Historical Purchase Analysis", value=True)
        purchase_time_str = st.text_input("YT Purchase Timestamp", "2024-07-25 23:00:00")
        invest_amount = st.number_input("Underlying Invested Amount", min_value=0.01, value=1.0, step=0.5)

        yt_purchase_dt: datetime | None = None
        if enable_analysis_1:
            try:
                yt_purchase_dt = datetime.fromisoformat(purchase_time_str.strip().replace("Z", "+00:00"))
                if yt_purchase_dt.tzinfo is None:
                    yt_purchase_dt = yt_purchase_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                st.error("Invalid historical purchase timestamp format")

        st.markdown("---")
        enable_analysis_2 = st.checkbox("Enable Limit Order Simulator", value=True)
        limit_time_str = st.text_input("Estimated Limit Execution Time", "2024-07-24 06:00:00")
        limit_implied_apy = st.number_input(
            "Target Implied APY", min_value=0.001, max_value=5.0, value=0.05, step=0.01, format="%.3f"
        )
        limit_invest_amount = st.number_input("Limit Order Investment Amount", min_value=0.01, value=1.0, step=0.5)

        limit_order_dt: datetime | None = None
        if enable_analysis_2:
            try:
                limit_order_dt = datetime.fromisoformat(limit_time_str.strip().replace("Z", "+00:00"))
                if limit_order_dt.tzinfo is None:
                    limit_order_dt = limit_order_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                st.error("Invalid limit order timestamp format")

    dark_mode = st.sidebar.toggle("Dark Theme", value=True)

    return SidebarState(
        network=network,
        market_contract=market_contract,
        yt_contract=yt_contract,
        start_time_str=start_time_str,
        quant_params=quant_params,
        tech_params=tech_params,
        dark_mode=dark_mode,
        selected_market_name=selected_market_name,
        enable_analysis_1=enable_analysis_1,
        yt_purchase_time_dt=yt_purchase_dt,
        underlying_invest_amount=float(invest_amount),
        enable_analysis_2=enable_analysis_2,
        limit_order_time_dt=limit_order_dt,
        limit_order_implied_apy=float(limit_implied_apy),
        limit_order_invest_amount=float(limit_invest_amount),
    )
