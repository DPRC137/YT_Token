"""Modern Streamlit presentation components: metric cards, tabs, and simulation summaries."""

from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from yt_token.analytics import (
    analyze_historical_purchase,
    simulate_limit_order,
)
from yt_token.indicators import apply_all_indicators
from yt_token.plotting import (
    plot_fair_value_comparison,
    plot_price_and_indicators,
    plot_volume_weighted_points,
    plot_yield_spread,
)
from yt_token.ui.sidebar import SidebarState


def render_header(symbol: str, network: str, maturity_time: datetime) -> None:
    """Render page title, badge metadata, and header banner."""
    st.markdown(
        f"""
        <div style="padding: 1.2rem 0rem; border-bottom: 1px solid rgba(128,128,128,0.2); margin-bottom: 1.5rem;">
            <h1 style="margin: 0; padding: 0; font-size: 2.2rem; font-weight: 700;">
                🪙 {symbol} <span style="font-size: 1.1rem; color: #888; font-weight: 400;">on {network.title()}</span>
            </h1>
            <p style="margin: 0.3rem 0 0 0; color: #888; font-size: 0.95rem;">
                Maturity Date: <b>{maturity_time.strftime("%Y-%m-%d %H:%M:%S UTC")}</b> &bull;
                Quantitative Fair Value Pricing & Yield Token Scanner
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(df: pd.DataFrame, implied_apy_avg: float, maturity_time: datetime) -> None:
    """Render top-level executive KPI metrics using Streamlit st.metric."""
    if df.empty:
        return

    latest = df.iloc[-1]
    hours_left = (maturity_time - latest["Time"]).total_seconds() / 3600.0
    days_left = max(0.0, hours_left / 24.0)

    cur_price = latest.get("yt/underlying", 0.0)
    cur_fair = latest.get("fair", 0.0)
    gap = cur_fair - cur_price
    cur_implied = latest.get("impliedApy", 0.0)
    cur_underlying = latest.get("underlyingApy", 0.0)
    cur_leverage = (1.0 / cur_price * 5.0) if cur_price > 0 else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Current YT Price",
            value=f"{cur_price:.4f}",
            help="Current Market Price of YT in units of underlying asset.",
        )
    with col2:
        st.metric(
            label="Fair Value Price",
            value=f"{cur_fair:.4f}",
            delta=f"{gap:+.4f} Spread",
            delta_color="normal",
            help="Theoretical fair price based on volume-weighted historical implied APY.",
        )
    with col3:
        st.metric(
            label="Implied APY",
            value=f"{cur_implied:.2%}",
            delta=f"{(cur_implied - cur_underlying):+.2%} vs Underlying",
            delta_color="inverse",
            help="Market priced Implied APY vs current underlying yield APY.",
        )
    with col4:
        st.metric(
            label="Estimated Leverage",
            value=f"{cur_leverage:.1f}x",
            help="Point leverage multiplier (includes 5x Pendle boost).",
        )
    with col5:
        st.metric(
            label="Time to Maturity",
            value=f"{days_left:.1f} Days",
            help=f"Hours remaining: {hours_left:.0f}h until maturity expiry.",
        )


def render_analysis_tabs(
    df: pd.DataFrame,
    implied_apy_average: float,
    h_range: pd.DatetimeIndex,
    fair_value_curve: np.ndarray,
    symbol: str,
    maturity_time: datetime,
    state: SidebarState,
) -> None:
    """Render structured tabbed analysis dashboard."""
    # Apply technical indicators
    df_enriched = apply_all_indicators(df, price_col="yt/underlying", params=state.tech_params)

    tab_overview, tab_valuation, tab_technical, tab_simulation, tab_data = st.tabs(
        [
            "📊 Overview & Valuation",
            "📈 Yield & Point Trajectory",
            "📉 Technical Analysis",
            "🎯 Investment & Limit Order Simulator",
            "📋 Historical Data & Export",
        ]
    )

    with tab_overview:
        st.markdown("### 💎 Fair Value Model & Valuation Spread")
        st.caption(
            "When the **YT Market Price** is *below* the **Fair Value Curve**, YT is undervalued relative to historical volume-weighted averages."
        )

        col_opts1, _ = st.columns([1, 4])
        with col_opts1:
            show_spread = st.checkbox("Show Valuation Spread Curve", value=True, key="tab1_spread")

        fig_fair = plot_fair_value_comparison(
            df_enriched,
            h_range,
            fair_value_curve,
            symbol=symbol,
            network=state.network,
            underlying_amount=state.quant_params.underlying_amount,
            show_difference=show_spread,
            dark_mode=state.dark_mode,
            annotation_dt=state.yt_purchase_time_dt if state.enable_analysis_1 else None,
        )
        st.plotly_chart(fig_fair, width="stretch")

        st.info(
            f"💡 **Volume-Weighted Implied APY Benchmark**: `{implied_apy_average:.2%}` used for continuous fair-value discounting."
        )

    with tab_valuation:
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            st.markdown("### 🌾 Long Yield APY vs. Implied APY")
            fig_yield = plot_yield_spread(
                df_enriched,
                symbol=symbol,
                network=state.network,
                dark_mode=state.dark_mode,
                annotation_dt=state.yt_purchase_time_dt if state.enable_analysis_1 else None,
            )
            st.plotly_chart(fig_yield, width="stretch")

        with col_y2:
            st.markdown("### 📦 Volume-Weighted Points Distribution")
            fig_vwp = plot_volume_weighted_points(
                df_enriched,
                symbol=symbol,
                network=state.network,
                dark_mode=state.dark_mode,
                annotation_dt=state.yt_purchase_time_dt if state.enable_analysis_1 else None,
            )
            st.plotly_chart(fig_vwp, width="stretch")

    with tab_technical:
        st.markdown("### 🔬 Technical Indicators & Moving Averages")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            show_mas = st.checkbox("Moving Averages (20/50/200)", value=True, key="ta_mas")
        with c2:
            show_vol = st.checkbox("Rolling Volatility", value=True, key="ta_vol")
        with c3:
            show_rsi = st.checkbox("RSI Indicator", value=False, key="ta_rsi")
        with c4:
            show_macd = st.checkbox("MACD & Signal", value=False, key="ta_macd")

        fig_tech = plot_price_and_indicators(
            df_enriched,
            symbol=symbol,
            network=state.network,
            dark_mode=state.dark_mode,
            show_volatility=show_vol,
            show_mas=show_mas,
            show_rsi=show_rsi,
            show_macd=show_macd,
            annotation_dt=state.yt_purchase_time_dt if state.enable_analysis_1 else None,
        )
        st.plotly_chart(fig_tech, width="stretch")

    with tab_simulation:
        st.markdown("### 🎯 Investment Payoff & Scenario Modeler")

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("#### 1. Historical Purchase Analysis")
            if state.enable_analysis_1 and state.yt_purchase_time_dt:
                analysis = analyze_historical_purchase(
                    df_enriched,
                    state.yt_purchase_time_dt,
                    maturity_time,
                    params=state.quant_params,
                    underlying_invest_amount=state.underlying_invest_amount,
                )
                if analysis:
                    st.success(
                        f"🎉 **You have outperformed {analysis.percentile_outperformed:.1f}% of all historical entry points!**"
                    )

                    res_df = pd.DataFrame(
                        [
                            {"Metric": "Purchase Timestamp", "Value": str(analysis.purchase_time)},
                            {"Metric": "YT Purchase Price", "Value": f"{analysis.yt_price:.4f} underlying"},
                            {"Metric": "Effective Leverage", "Value": f"{analysis.leverage:.2f}x"},
                            {"Metric": "Total Points at Maturity", "Value": f"{analysis.points_at_maturity:,.2f}"},
                            {"Metric": "Points per Underlying", "Value": f"{analysis.points_per_underlying:,.2f}"},
                            {"Metric": "Cost per 1.0 Point", "Value": f"{analysis.cost_per_point:.8f} underlying"},
                            {"Metric": "Market Average Points", "Value": f"{analysis.market_avg_points:,.2f}"},
                            {"Metric": "Market Maximum Points", "Value": f"{analysis.market_max_points:,.2f}"},
                            {"Metric": "Market Minimum Points", "Value": f"{analysis.market_min_points:,.2f}"},
                        ]
                    )
                    st.table(res_df.set_index("Metric"))
                else:
                    st.warning("Could not calculate historical purchase performance.")
            else:
                st.info("Enable Historical Purchase Analysis in the sidebar to view metrics.")

        with col_s2:
            st.markdown("#### 2. Limit Order Scenario Simulator")
            if state.enable_analysis_2 and state.limit_order_time_dt:
                sim = simulate_limit_order(
                    df_enriched,
                    state.limit_order_time_dt,
                    state.limit_order_implied_apy,
                    maturity_time,
                    params=state.quant_params,
                    underlying_invest_amount=state.limit_order_invest_amount,
                )
                if sim:
                    st.success(
                        f"🎉 **Target limit order would outperform {sim.percentile_outperformed:.1f}% of historical buyers!**"
                    )

                    sim_df = pd.DataFrame(
                        [
                            {"Metric": "Execution Timestamp", "Value": str(sim.estimated_time)},
                            {"Metric": "Target Implied APY", "Value": f"{sim.implied_apy:.2%}"},
                            {"Metric": "Simulated YT Price", "Value": f"{sim.simulated_price:.4f} underlying"},
                            {"Metric": "Effective Leverage", "Value": f"{sim.leverage:.2f}x"},
                            {"Metric": "Projected Points at Maturity", "Value": f"{sim.simulated_points:,.2f}"},
                            {"Metric": "Projected Points / Underlying", "Value": f"{sim.points_per_underlying:,.2f}"},
                            {"Metric": "Market Average Points", "Value": f"{sim.market_avg_points:,.2f}"},
                            {"Metric": "Market Maximum Points", "Value": f"{sim.market_max_points:,.2f}"},
                        ]
                    )
                    st.table(sim_df.set_index("Metric"))
                else:
                    st.warning("Could not simulate limit order.")
            else:
                st.info("Enable Limit Order Simulator in the sidebar to simulate orders.")

    with tab_data:
        st.markdown("### 📋 Historical Market & Indicator Time Series")
        display_cols = [
            c
            for c in [
                "Time",
                "yt/underlying",
                "fair",
                "difference",
                "impliedApy",
                "underlyingApy",
                "points",
                "volume",
                "RSI",
                "MACD",
            ]
            if c in df_enriched.columns
        ]
        st.dataframe(
            df_enriched[display_cols].sort_values("Time", ascending=False),
            width="stretch",
            height=380,
        )

        csv = df_enriched.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"{symbol}_{state.network}_pendle_yt_analysis.csv",
            mime="text/csv",
        )
