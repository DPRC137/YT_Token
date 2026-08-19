import re
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import plotly.graph_objects as go
import numpy as np
from io import StringIO

def is_valid_address(address):
    """Validates if the provided string is a valid EVM contract address (0x followed by 40 hex chars)."""
    if not isinstance(address, str):
        return False
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", address))

# Set up the session with retries
session = requests.session()
retry = requests.packages.urllib3.util.retry.Retry(total=3, backoff_factor=1)
session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retry))
session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retry))

# User Inputs
st.title("Pendle Finance Yield Token Analysis")

network = st.selectbox('Select Network', ['ethereum', 'arbitrum', 'mantle'], index=0)
market_contract = st.text_input('Market Contract Address', '0x00b321d89a8c36b3929f20b7955080baed706d1b')
yt_contract = st.text_input('Yield Token Contract Address', '0x4f0b4e6512630480b868e62a8a1d3451b0e9192d')
start_time = st.text_input('Start Time (UTC)', '2023-01-01 00:00:00')
underlying_amount = st.number_input('Underlying Amount', 1)
points_per_hour_per_underlying = st.number_input('Points per Hour per Underlying', 0.04)
pendle_yt_multiplier = st.number_input('Pendle YT Multiplier', 5)
dark_mode = st.checkbox('Dark Mode')

turn_on_auto_analysis_1 = st.checkbox('Turn On Auto-Analyze Investment Situation')
yt_purchase_time = st.text_input('YT Purchase Time', '2024-07-25 23:00:00')
underlying_invest_amount = st.number_input('Underlying Invest Amount', 1)

turn_on_auto_analysis_2 = st.checkbox('Turn On Simulated Limit Order Analysis')
limmit_order_yt_estimated_purchase_time = st.text_input('Estimated Purchase Time for Limit Order', '2024-07-24 06:00:00')
limmit_order_implied_apy_0_to_1 = st.number_input('Limit Order Implied APY (0 to 1)', 0.05)
limmit_order_underlying_invest_amount = st.number_input('Limit Order Underlying Invest Amount', 1)

volatility_window = st.number_input('Volatility Window', 48)
ma1 = st.number_input('Moving Average 1 (e.g., 20-day)', 24)
ma2 = st.number_input('Moving Average 2 (e.g., 50-day)', 72)
ma3 = st.number_input('Moving Average 3 (e.g., 200-day)', 216)
rsi_window = st.number_input('RSI Window', 72)
ema1 = st.number_input('EMA1 Window', 12)
ema2 = st.number_input('EMA2 Window', 26)
macd_signal = st.number_input('MACD Signal Window', 9)

# Set up network IDs
network_ids = {
    'arbitrum': '/42161',
    'ethereum': '/1',
    'mantle': '/5000'
}

network_id = network_ids.get(network.lower())
if network_id is not None:
    url = f'https://api-v2.pendle.finance/core/v1{network_id}/assets/all'
else:
    st.error("Unsupported network type")
    st.stop()

headers = {
    "User-Agent": "Mozilla/5.0"
}

@st.cache_data
def fetch_assets_data(url):
    response = session.get(url, headers=headers)
    return response.json()

data = fetch_assets_data(url)

def find_valid_assets(data, base_type, expiry_key, address):
    valid_assets = [
        item for item in data
        if item.get('baseType') == base_type and
           item.get('address') == address and
           expiry_key in item
    ]
    return valid_assets


def add_purchase_time_annotation(fig, x_value, y_value, text="YT Purchase Time"):
    fig.add_vline(x=x_value, line_width=3, line_dash="dash", line_color="green")
    fig.add_annotation(
        x=x_value,
        y=y_value,
        text=text,
        showarrow=True,
        arrowhead=1,
        ax=20,
        ay=-30
    )

valid_assets = find_valid_assets(data, 'YT', 'expiry', yt_contract)
if valid_assets:
    symbol = valid_assets[0]['symbol']
    maturity = valid_assets[0]['expiry']
else:
    st.error("No valid assets found.")
    st.stop()

# Convert start time to ISO format and make it timezone-aware
datetime_obj = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
start_time_str = datetime_obj.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
points = points_per_hour_per_underlying
mode = 'plotly_dark' if dark_mode else 'plotly_white'

@st.cache_data
def fetch_yteth_ohlcv_data(url, start_time_str, end_time_str, _session=None):
    if not url:
        return pd.DataFrame(columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
    if _session is None:
        _session = session
    params = {
        "time_frame": "hour",
        "timestamp_start": start_time_str,
        "timestamp_end": end_time_str
    }
    response = _session.get(url, headers=headers, params=params)
    results = response.json().get('results', [])
    if not results:
        return pd.DataFrame(columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df = pd.DataFrame(results)
    df['Time'] = pd.to_datetime(df['time'], format='ISO8601', utc=True)
    if 'volume' not in df.columns:
        df['Volume'] = 0
    else:
        df['Volume'] = df['volume'].fillna(0)
    return df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close'
    })[['Time', 'Open', 'High', 'Low', 'Close', 'Volume']]

@st.cache_data
def fetch_apy_data(url, start_time_str, end_time_str, _session=None):
    if not url:
        return pd.DataFrame()
    if _session is None:
        _session = session
    params = {
        "time_frame": "hour",
        "timestamp_start": start_time_str,
        "timestamp_end": end_time_str
    }
    response = _session.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            csv_data = data['results']
            if not csv_data:
                return pd.DataFrame()
            df = pd.read_csv(StringIO(csv_data))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            return df
        else:
            st.error("No results found in the API response")
            return pd.DataFrame()
    else:
        st.error(f"Failed to retrieve data with status code: {response.status_code}")
        return pd.DataFrame()

# Main Class for Data Acquisition and Analysis
class Main:
    def __init__(self, market_contract, yt_contract, start_time_str, network):
        self.session = session
        self.market_contract = market_contract
        self.yt_contract = yt_contract
        self.start_time_str = start_time_str
        self.end_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        self.interval = '1h'
        self.url_apy = None
        self.url_ohlcv_yteth = None

        if not is_valid_address(self.market_contract):
            st.error("Invalid market contract address format.")
            return

        if not is_valid_address(self.yt_contract):
            st.error("Invalid yield token contract address format.")
            return

        network_id = network_ids.get(network.lower())
        if network_id is not None:
            self.url_apy = f'https://api-v2.pendle.finance/core/v1{network_id}/markets/{self.market_contract}/apy-history-1ma'
            self.url_ohlcv_yteth = f'https://api-v2.pendle.finance/core/v3{network_id}/prices/{self.yt_contract}/ohlcv'
        else:
            st.error("Unsupported network type")

    def fetch_yteth_ohlcv(self):
        if not self.url_ohlcv_yteth:
            return pd.DataFrame(columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        return fetch_yteth_ohlcv_data(self.url_ohlcv_yteth, self.start_time_str, self.end_time_str, _session=self.session)

    def fetch_apy(self):
        if not self.url_apy:
            st.error("Unsupported network type")
            return pd.DataFrame()
        return fetch_apy_data(self.url_apy, self.start_time_str, self.end_time_str, _session=self.session)

    def run(self):
        df = self.fetch_apy()
        volume = self.fetch_yteth_ohlcv()['Volume']
        if not df.empty:
            df['volume'] = volume
            return df
        else:
            st.error("No data to display.")
            return pd.DataFrame()

main_instance = Main(market_contract, yt_contract, start_time_str, network=network)
df = main_instance.run()

if not df.empty:
    maturity_time = datetime.fromisoformat(maturity.replace('Z', '+00:00'))
    df['hours_to_maturity'] = (maturity_time - df['timestamp']).dt.total_seconds() / 3600
    df['Time'] = pd.to_datetime(df['timestamp'], utc=True)
    df['yt/underlying'] = (df['impliedApy'] + 1)**(df['hours_to_maturity']/8760) - 1
    df['long_yield_apy'] = (1 + (df['underlyingApy'] - df['impliedApy']) / (df['impliedApy'])) ** (8760 / df['hours_to_maturity']) - 1

    price = df['yt/underlying']
    time_diff_hours = (maturity_time - df['Time']).dt.total_seconds() / 3600
    df['points'] = 1 / price * time_diff_hours * points * underlying_amount * pendle_yt_multiplier
    h_range = pd.date_range(start=df['Time'].iloc[0], end=maturity_time, freq='h')

    implied_apy_average = (df['impliedApy'] * df['volume'] / df['volume'].sum()).sum()

    fair_value_curve = 1 - 1 / (1 + implied_apy_average) ** (((maturity_time - h_range).total_seconds() / 3600) / 8760)

    df['weighted_points'] = df['points'] * df['volume'] / (df['volume'].sum())
    weighted_points_per_underlying = df['weighted_points'].sum()
    df['fair'] = fair_value_curve[:len(df)]
    df['difference'] = (df['fair'] - df['yt/underlying'])

    # Auto-Analyze Investment Situation
    if turn_on_auto_analysis_1:
        yt_purchase_time_dt = datetime.fromisoformat(yt_purchase_time.replace('Z', '+00:00'))
        nearest_times = df['Time'].sort_values().unique()
        previous_time = nearest_times[nearest_times <= yt_purchase_time_dt].max()
        next_time = nearest_times[nearest_times > yt_purchase_time_dt].min()

        if previous_time and next_time:
            distance_to_previous = (yt_purchase_time_dt - previous_time).total_seconds()
            distance_to_next = (next_time - yt_purchase_time_dt).total_seconds()

            weight_previous = distance_to_next / (distance_to_previous + distance_to_next)
            weight_next = distance_to_previous / (distance_to_previous + distance_to_next)

            yt_price_when_purchase = (
                weight_previous * df[df['Time'] == previous_time]['yt/underlying'].values[0]
                + weight_next * df[df['Time'] == next_time]['yt/underlying'].values[0]
            )

            volume_when_purchase = (
                weight_previous * df[df['Time'] == previous_time]['volume'].values[0]
                + weight_next * df[df['Time'] == next_time]['volume'].values[0]
            )

            time_diff_hours_for_auto_analysis = (maturity_time - yt_purchase_time_dt).total_seconds() / 3600
            lever = 1 / yt_price_when_purchase * pendle_yt_multiplier
            points_for_auto_analysis = 1 / yt_price_when_purchase * time_diff_hours_for_auto_analysis * points * underlying_invest_amount * pendle_yt_multiplier

            points_for_auto_analysis_per_underlying = points_for_auto_analysis / underlying_invest_amount
            exceed_count = df[df['points'] < points_for_auto_analysis_per_underlying].shape[0]
            total_count = df.shape[0]
            percent_exceed = (exceed_count / total_count) * 100

            st.write(f"### Auto-Analyze Investment Situation")
            st.write(f"Purchase Time: {yt_purchase_time}")
            st.write(f"YT Purchase Price: {yt_price_when_purchase:.4f}")
            st.write(f"Leverage (include pendle_yt_multiplier): {lever:.2f}x")
            st.write(f"Points at Maturity: {points_for_auto_analysis:.2f} points")
            st.write(f"Points per Unit of Underlying Asset at Maturity: {points_for_auto_analysis_per_underlying:.2f} points")
            st.write(f"Cost per Unit of Point at Maturity: {1 / points_for_auto_analysis_per_underlying:.8f} underlying/point")
            st.write(f"Market Maximum Points per Unit at Maturity: {df['points'].max():.2f} points")
            st.write(f"Market Minimum Points per Unit at Maturity: {df['points'].min():.2f} points")
            st.write(f"Market Average Points per Unit at Maturity: {weighted_points_per_underlying:.2f} points")
            st.write(f"🎉 You have outperformed {percent_exceed:.2f}% of users!")

    # Simulated Limit Order Results
    if turn_on_auto_analysis_2:
        limmit_order_yt_purchase_time_dt = datetime.fromisoformat(limmit_order_yt_estimated_purchase_time.replace('Z', '+00:00'))
        limmit_order_yt_price_when_purchase = (limmit_order_implied_apy_0_to_1 + 1) ** ((maturity_time - limmit_order_yt_purchase_time_dt).total_seconds() / 31536000) - 1

        limmit_order_time_diff_hours_for_auto_analysis = (maturity_time - limmit_order_yt_purchase_time_dt).total_seconds() / 3600
        limmit_order_lever = 1 / limmit_order_yt_price_when_purchase * pendle_yt_multiplier
        limmit_order_points_for_auto_analysis = 1 / limmit_order_yt_price_when_purchase * limmit_order_time_diff_hours_for_auto_analysis * points * limmit_order_underlying_invest_amount * pendle_yt_multiplier

        limmit_order_points_for_auto_analysis_per_underlying = limmit_order_points_for_auto_analysis / limmit_order_underlying_invest_amount
        limmit_order_weighted_points_for_auto_analysis_per_underlying = df['volume'].mean() / df['volume'].sum() * limmit_order_points_for_auto_analysis_per_underlying
        limmit_order_exceed_count = df[df['weighted_points'] < limmit_order_weighted_points_for_auto_analysis_per_underlying].shape[0]
        limmit_order_total_count = df.shape[0]
        limmit_order_percent_exceed = (limmit_order_exceed_count / limmit_order_total_count) * 100

        st.write(f"### Simulated Limit Order Results")
        st.write(f"Estimated Purchase Time: {limmit_order_yt_estimated_purchase_time}")
        st.write(f"Limit Order YT Purchase Price: {limmit_order_yt_price_when_purchase:.4f}")
        st.write(f"Leverage (include pendle_yt_multiplier): {limmit_order_lever:.2f}x")
        st.write(f"Points at Maturity: {limmit_order_points_for_auto_analysis:.2f} points")
        st.write(f"Points per Unit of Underlying Asset at Maturity: {limmit_order_points_for_auto_analysis_per_underlying:.2f} points")
        st.write(f"Market Maximum Points per Unit at Maturity: {df['points'].max():.2f} points")
        st.write(f"Market Minimum Points per Unit at Maturity: {df['points'].min():.2f} points")
        st.write(f"Market Average Points per Unit at Maturity: {weighted_points_per_underlying:.2f} points")
        st.write(f"🎉 You will outperform {limmit_order_percent_exceed:.2f}% of users!")

    # Custom Indicators
    if len(df) >= volatility_window:
        df['volatility'] = df['yt/underlying'].rolling(window=volatility_window).std().bfill()
    else:
        df['volatility'] = np.nan
        st.warning('Volatility window is too large for the available data')

    df['moving_average_20'] = df['yt/underlying'].rolling(window=ma1).mean().bfill()
    df['moving_average_50'] = df['yt/underlying'].rolling(window=ma2).mean().bfill()
    df['moving_average_200'] = df['yt/underlying'].rolling(window=ma3).mean().bfill()

    if len(df) >= rsi_window:
        delta = df['yt/underlying'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_window).mean().bfill()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_window).mean().bfill()
        rs = gain / loss
        df['RSI'] = (100 - (100 / (1 + rs))).bfill()
    else:
        df['RSI'] = np.nan

    ema12 = df['yt/underlying'].ewm(span=ema1, adjust=False).mean().bfill()
    ema26 = df['yt/underlying'].ewm(span=ema2, adjust=False).mean().bfill()
    df['MACD'] = ema12 - ema26
    df['Signal Line'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean().bfill()

    # YT Price Curve Visualization
    add_volatility = st.checkbox('Add Volatility Curve')
    add_moving_average = st.checkbox('Add Moving Averages')
    add_RSI = st.checkbox('Add RSI')
    add_macd = st.checkbox('Add MACD')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Time'], y=df['yt/underlying'], mode='lines', name='YT Price'))

    if add_volatility:
        fig.add_trace(go.Scatter(x=df['Time'], y=df['volatility'], mode='lines', name='Volatility', yaxis='y2'))
    if add_moving_average:
        fig.add_trace(go.Scatter(x=df['Time'], y=df['moving_average_20'], mode='lines', name='20-day MA', yaxis='y'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['moving_average_50'], mode='lines', name='50-day MA', yaxis='y'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['moving_average_200'], mode='lines', name='200-day MA', yaxis='y'))
    if add_RSI:
        fig.add_trace(go.Scatter(x=df['Time'], y=df['RSI'], mode='lines', name='RSI', yaxis='y3'))
    if add_macd:
        fig.add_trace(go.Scatter(x=df['Time'], y=df['MACD'], mode='lines', name='MACD', yaxis='y4'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['Signal Line'], mode='lines', name='Signal Line', yaxis='y4'))

    fig.update_layout(
        title=f'{symbol} on {network} YT/Underlying asset',
        xaxis_title='Time',
        yaxis_title='YT Price (per Underlying)',
        template=mode,
        yaxis2=dict(
            title='Volatility',
            overlaying='y',
            side='right',
            position=0.85
        ),
        yaxis3=dict(
            title='RSI',
            overlaying='y',
            side='right',
            position=0.90
        ),
        yaxis4=dict(
            title='MACD',
            overlaying='y',
            side='right',
            position=0.95
        )
    )

    if turn_on_auto_analysis_1:
        add_purchase_time_annotation(fig, yt_purchase_time_dt, max(df['yt/underlying']))

    st.plotly_chart(fig)

    # Total Points Earned Visualization
    fig = go.Figure(data=go.Scatter(x=df['Time'], y=df['points'], mode='lines'))
    fig.update_layout(
        title=f'{symbol} on {network} | Total Points Earned from {underlying_amount} Underlying Investment in YT at a Certain Time',
        xaxis_title='Time',
        yaxis_title='Points',
        template=mode
    )

    if turn_on_auto_analysis_1:
        add_purchase_time_annotation(fig, yt_purchase_time_dt, max(df['yt/underlying']))

    st.plotly_chart(fig)

    # YT Price/Points Earned/Fair Value Curve Visualization
    Add_difference_curve = st.checkbox('Add Difference Curve')

    if not Add_difference_curve:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Time'], y=df['yt/underlying'], mode='lines', name='YT Price', yaxis='y'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['points'], mode='lines', name='Points Earned', yaxis='y2'))

        fig.update_layout(
            title=f'{symbol} on {network} [{underlying_amount} underlying coin] | BUY YT WHEN THE YT Price IS UNDER THE FAIR VALUE CURVE TO MAXIMIZE POINTS EARNED',
            xaxis_title='Certain Time of Purchasing YT',
            yaxis=dict(title='YT Price', side='left'),
            yaxis2=dict(title='Points Earned', overlaying='y', side='right'),
            template=mode
        )

        fig.add_trace(go.Scatter(
            x=h_range,
            y=fair_value_curve,
            mode='lines',
            name='Fair Value Curve of YT',
            line=dict(color='yellow', dash='dot', width=3),
            yaxis='y'
        ))

    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Time'], y=df['yt/underlying'], mode='lines', name='YT Price', yaxis='y'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['points'], mode='lines', name='Points Earned', yaxis='y2'))
        fig.add_trace(go.Scatter(x=df['Time'], y=df['difference'], mode='lines', name='Difference between Fair and Market Price', yaxis='y3'))

        fig.update_layout(
            title=f'{symbol} on {network} [{underlying_amount} underlying coin] | BUY YT WHEN THE YT Price IS UNDER THE FAIR VALUE CURVE TO MAXIMIZE POINTS EARNED',
            xaxis_title='Certain Time of Purchasing YT',
            yaxis=dict(title='YT Price', side='left'),
            yaxis2=dict(title='Points Earned', overlaying='y', side='right'),
            yaxis3=dict(title='Difference', overlaying='y', side='right'),
            template=mode
        )

        fig.add_trace(go.Scatter(
            x=h_range,
            y=fair_value_curve,
            mode='lines',
            name='Fair Value Curve of YT',
            line=dict(color='yellow', dash='dot', width=3),
            yaxis='y'
        ))

    if turn_on_auto_analysis_1:
        add_purchase_time_annotation(fig, yt_purchase_time_dt, max(df['yt/underlying']) * 0.01)

    st.plotly_chart(fig)

    # Long Yield APY vs. Implied APY Visualization
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Time'], y=df['long_yield_apy'], mode='lines', name='Long Yield APY', yaxis='y'))
    fig.add_trace(go.Scatter(x=df['Time'], y=df['impliedApy'], mode='lines', name='Implied APY', yaxis='y2'))

    fig.update_layout(
        title=f'{symbol} on {network} | Long Yield APY vs. Implied APY',
        xaxis_title='Certain Time of Purchasing YT',
        yaxis=dict(title='Long Yield APY', side='left'),
        yaxis2=dict(title='Implied APY', overlaying='y', side='right'),
        template=mode
    )

    if turn_on_auto_analysis_1:
        add_purchase_time_annotation(fig, yt_purchase_time_dt, max(df['long_yield_apy']))

    st.plotly_chart(fig)

    # Weighted Points (by Volume) Over Time Visualization
    fig = go.Figure(data=go.Scatter(x=df['Time'], y=df['weighted_points'], mode='lines'))
    fig.update_layout(
        title=f'{symbol} on {network} | Weighted Points (by Volume) Over Time',
        xaxis_title='Time',
        yaxis_title='Weighted Points',
        template=mode
    )

    if turn_on_auto_analysis_1:
        add_purchase_time_annotation(fig, yt_purchase_time_dt, max(df['weighted_points']))

    st.plotly_chart(fig)

    st.write(f'The weighted Implied APY used to calculate the fair value curve is: {implied_apy_average:.2%}')
else:
    st.error("No valid data to display.")
