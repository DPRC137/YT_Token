"""YT_Token - Quantitative Analytics & Fair Price Valuation Engine for Pendle Finance Yield Tokens."""

__version__ = "1.0.0"
__author__ = "DPR"

from yt_token.client import (
    PendleApiClient,
    fetch_apy_data,
    fetch_assets_data,
    fetch_yteth_ohlcv_data,
    find_valid_assets,
    is_valid_address,
)
from yt_token.config import MARKET_PRESETS, NETWORK_IDS, QuantitativeParams, TechnicalParams
from yt_token.models import Asset, InvestmentAnalysis, LimitOrderSimulation, MarketSummary
from yt_token.plotting import add_purchase_time_annotation

__all__ = [
    "is_valid_address",
    "find_valid_assets",
    "fetch_assets_data",
    "fetch_yteth_ohlcv_data",
    "fetch_apy_data",
    "add_purchase_time_annotation",
    "PendleApiClient",
    "Asset",
    "MarketSummary",
    "InvestmentAnalysis",
    "LimitOrderSimulation",
    "QuantitativeParams",
    "TechnicalParams",
    "MARKET_PRESETS",
    "NETWORK_IDS",
]
