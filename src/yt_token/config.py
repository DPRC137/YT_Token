"""Configuration, network mapping, presets, and constants for Pendle YT analytics."""

from dataclasses import dataclass

# Supported EVM Networks and Chain IDs in Pendle v2
NETWORK_IDS: dict[str, str] = {
    "ethereum": "/1",
    "arbitrum": "/42161",
    "mantle": "/5000",
    "optimism": "/10",
    "base": "/8453",
    "bsc": "/56",
}

DEFAULT_NETWORK = "ethereum"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = "YT-Token-Scanner/1.0 (Quantitative Analytics Engine)"

API_BASE_V1 = "https://api-v2.pendle.finance/core/v1"
API_BASE_V3 = "https://api-v2.pendle.finance/core/v3"


@dataclass(frozen=True)
class MarketPreset:
    """Pre-configured Pendle market for user convenience."""

    name: str
    network: str
    market_address: str
    yt_address: str
    description: str


MARKET_PRESETS: list[MarketPreset] = [
    MarketPreset(
        name="Ethereum • USDe (Default / Reference)",
        network="ethereum",
        market_address="0x00b321d89a8c36b3929f20b7955080baed706d1b",
        yt_address="0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
        description="Ethena USDe yield market on Ethereum mainnet",
    ),
    MarketPreset(
        name="Ethereum • eETH",
        network="ethereum",
        market_address="0x7d49e5ab516d4738262d097771e8633fe3d60ec8",
        yt_address="0x25a95610e206013a7c644ca70ad255b6eb2690ff",
        description="ether.fi eETH LRT market on Ethereum mainnet",
    ),
    MarketPreset(
        name="Arbitrum • rsETH",
        network="arbitrum",
        market_address="0x8929e71ab85c276bc38ea5f72cf72fa821cb9142",
        yt_address="0x347c61f2f01f01651e737c76a91176b6efd87508",
        description="Kelp DAO rsETH market on Arbitrum",
    ),
    MarketPreset(
        name="Mantle • mETH",
        network="mantle",
        market_address="0xc27ef647614e7a68e6f1fca63571d87ee9fb01a4",
        yt_address="0x15f2bfa32b13c72b22f77839352e809315bcda63",
        description="Mantle LSP mETH market",
    ),
]


@dataclass
class QuantitativeParams:
    """Hyperparameters for quantitative pricing, leverage and point farming models."""

    underlying_amount: float = 1.0
    points_per_hour_per_underlying: float = 0.04
    pendle_yt_multiplier: float = 5.0
    annual_hours: float = 8760.0  # 365 days * 24 hours


@dataclass
class TechnicalParams:
    """Hyperparameters for technical analysis indicators."""

    volatility_window: int = 48
    ma1_window: int = 24
    ma2_window: int = 72
    ma3_window: int = 216
    rsi_window: int = 72
    ema_fast_window: int = 12
    ema_slow_window: int = 26
    macd_signal_window: int = 9
