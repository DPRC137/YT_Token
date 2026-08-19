"""Unit tests for API Client, session creation, and address validation."""

from unittest.mock import MagicMock

import pytest

from yt_token.client import (
    PendleApiClient,
    UnsupportedNetworkError,
    fetch_apy_data,
    fetch_yteth_ohlcv_data,
    find_valid_assets,
    is_valid_address,
)


def test_is_valid_address_valid():
    valid = [
        "0x00b321d89a8c36b3929f20b7955080baed706d1b",
        "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
        "0x0000000000000000000000000000000000000000",
        "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
    ]
    for addr in valid:
        assert is_valid_address(addr) is True


def test_is_valid_address_invalid():
    invalid = [
        "0x00b321d89a8c36b3929f20b7955080baed706d1",  # 39 chars
        "0x00b321d89a8c36b3929f20b7955080baed706d1bb",  # 41 chars
        "0x00b321d89a8c36b3929f20b7955080baed706d1g",  # invalid hex 'g'
        None,
        12345,
        "",
        "SELECT * FROM users",
    ]
    for addr in invalid:
        assert is_valid_address(addr) is False


def test_find_valid_assets(sample_assets_raw):
    # Valid match
    yt_assets = find_valid_assets(sample_assets_raw, "YT", "expiry", "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d")
    assert len(yt_assets) == 1
    assert yt_assets[0]["symbol"] == "YT-USDe-31DEC2024"

    # Match PT
    pt_assets = find_valid_assets(sample_assets_raw, "PT", "expiry", "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d")
    assert len(pt_assets) == 1
    assert pt_assets[0]["symbol"] == "PT-USDe-31DEC2024"

    # Non-existent
    none_assets = find_valid_assets(sample_assets_raw, "YT", "expiry", "0x0000000000000000000000000000000000000000")
    assert len(none_assets) == 0


def test_pendle_api_client_unsupported_network():
    with pytest.raises(UnsupportedNetworkError):
        PendleApiClient(network="solana")


def test_pendle_api_client_urls():
    client = PendleApiClient(network="ethereum")
    assert client.get_assets_url() == "https://api-v2.pendle.finance/core/v1/1/assets/all"
    assert (
        client.get_market_apy_url("0x00b321d89a8c36b3929f20b7955080baed706d1b")
        == "https://api-v2.pendle.finance/core/v1/1/markets/0x00b321d89a8c36b3929f20b7955080baed706d1b/apy-history-1ma"
    )
    assert (
        client.get_yt_ohlcv_url("0x4f0b4e6512630480b868e62a8a1d3451b0e9192d")
        == "https://api-v2.pendle.finance/core/v3/1/prices/0x4f0b4e6512630480b868e62a8a1d3451b0e9192d/ohlcv"
    )


def test_fetch_apy_data_mocked():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": "timestamp,impliedApy,underlyingApy\n1704067200,0.05,0.08\n1704070800,0.06,0.09\n"
    }
    mock_session.get.return_value = mock_response

    df = fetch_apy_data(
        "http://mock/apy", "2024-01-01T00:00:00.000Z", "2024-01-02T00:00:00.000Z", _session=mock_session
    )
    assert not df.empty
    assert len(df) == 2
    assert "timestamp" in df.columns
    assert "impliedApy" in df.columns


def test_fetch_ohlcv_data_mocked():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"time": "2024-01-01T00:00:00Z", "open": 0.05, "high": 0.06, "low": 0.04, "close": 0.055, "volume": 500}
        ]
    }
    mock_session.get.return_value = mock_response

    df = fetch_yteth_ohlcv_data(
        "http://mock/ohlcv", "2024-01-01T00:00:00.000Z", "2024-01-02T00:00:00.000Z", _session=mock_session
    )
    assert not df.empty
    assert len(df) == 1
    assert list(df.columns) == ["Time", "Open", "High", "Low", "Close", "Volume"]
    assert df["Volume"].iloc[0] == 500


def test_fetch_active_markets_mocked():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "name": "Market A",
                "symbol": "MKT-A",
                "address": "0x00b321d89a8c36b3929f20b7955080baed706d1b",
                "yt": {"address": "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d", "symbol": "YT-A"},
                "expiry": "2024-12-31T00:00:00Z",
                "liquidity": {"usd": 5000000.0},
                "tradingVolume": {"usd": 100000.0},
                "impliedApy": 0.05,
                "underlyingApy": 0.08,
            }
        ]
    }
    mock_session.get.return_value = mock_response

    client = PendleApiClient(network="ethereum", session=mock_session)
    markets = client.fetch_active_markets()

    assert len(markets) == 1
    m = markets[0]
    assert m.name == "Market A"
    assert m.market_address == "0x00b321d89a8c36b3929f20b7955080baed706d1b"
    assert m.yt_address == "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d"
    assert m.liquidity_usd == 5000000.0
    assert "Liq: $5,000,000" in m.display_label
