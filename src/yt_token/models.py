"""Domain dataclasses and typed models for Pendle YT analytics."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Asset:
    """Represents a Pendle asset (YT, PT, LP, SY)."""

    address: str
    symbol: str
    base_type: str
    expiry: str | None = None
    name: str | None = None
    decimals: int = 18

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Asset":
        return cls(
            address=data.get("address", "").lower(),
            symbol=data.get("symbol", ""),
            base_type=data.get("baseType", ""),
            expiry=data.get("expiry"),
            name=data.get("name"),
            decimals=data.get("decimals", 18),
        )


@dataclass
class DiscoveredMarket:
    """Represents an active market pool dynamically fetched from Pendle API."""

    name: str
    symbol: str
    network: str
    market_address: str
    yt_address: str
    expiry: str
    liquidity_usd: float = 0.0
    trading_volume_usd: float = 0.0
    implied_apy: float = 0.0
    underlying_apy: float = 0.0

    @property
    def display_label(self) -> str:
        exp_short = self.expiry[:10] if self.expiry else "N/A"
        liq_str = f"${self.liquidity_usd:,.0f}" if self.liquidity_usd > 0 else ""
        if liq_str:
            return f"{self.name} (Exp: {exp_short}) • Liq: {liq_str}"
        return f"{self.name} (Exp: {exp_short})"


@dataclass
class InvestmentAnalysis:
    """Results from evaluating a historical YT purchase point."""

    purchase_time: datetime
    yt_price: float
    leverage: float
    points_at_maturity: float
    points_per_underlying: float
    cost_per_point: float
    market_max_points: float
    market_min_points: float
    market_avg_points: float
    percentile_outperformed: float


@dataclass
class LimitOrderSimulation:
    """Results from evaluating a simulated future limit order."""

    estimated_time: datetime
    implied_apy: float
    simulated_price: float
    leverage: float
    simulated_points: float
    points_per_underlying: float
    market_max_points: float
    market_min_points: float
    market_avg_points: float
    percentile_outperformed: float


@dataclass
class MarketSummary:
    """Current top-level metrics for the selected YT market."""

    symbol: str
    network: str
    maturity_date: datetime
    hours_to_maturity: float
    current_implied_apy: float
    current_underlying_apy: float
    current_yt_price: float
    fair_value_price: float
    valuation_gap: float  # (Fair - Market)
    current_leverage: float
    volume_weighted_implied_apy: float
    total_volume: float
