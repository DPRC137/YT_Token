import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ytTok import is_valid_address, Main, add_purchase_time_annotation

class TestytTokValidation(unittest.TestCase):
    def test_is_valid_address_valid(self):
        valid_addresses = [
            "0x00b321d89a8c36b3929f20b7955080baed706d1b",
            "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            "0x0000000000000000000000000000000000000000",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        ]
        for addr in valid_addresses:
            self.assertTrue(is_valid_address(addr), f"Address {addr} should be valid")

    def test_is_valid_address_invalid(self):
        invalid_addresses = [
            "0x00b321d89a8c36b3929f20b7955080baed706d1",   # Too short (39 hex)
            "0x00b321d89a8c36b3929f20b7955080baed706d1bb", # Too long (41 hex)
            "0x00b321d89a8c36b3929f20b7955080baed706d1g",  # Non-hex character
            "../0x00b321d89a8c36b3929f20b7955080baed706d1b", # Path traversal attempt
            "0x00b321d89a8c36b3929f20b7955080baed706d1b/../../",
            "SELECT * FROM users",                        # Injection string
            None,
            12345,
            "",
        ]
        for addr in invalid_addresses:
            self.assertFalse(is_valid_address(addr), f"Address {addr} should be invalid")

    @patch('streamlit.error')
    def test_main_with_invalid_market_contract(self, mock_st_error):
        main = Main(
            market_contract="invalid_contract",
            yt_contract="0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            start_time_str="2023-01-01T00:00:00.000Z",
            network="ethereum"
        )
        self.assertIsNone(main.url_apy)
        self.assertIsNone(main.url_ohlcv_yteth)
        mock_st_error.assert_called_with("Invalid market contract address format.")

        df_apy = main.fetch_apy()
        self.assertTrue(df_apy.empty)

        df_ohlcv = main.fetch_yteth_ohlcv()
        self.assertTrue(df_ohlcv.empty)

    @patch('streamlit.error')
    def test_main_with_invalid_yt_contract(self, mock_st_error):
        main = Main(
            market_contract="0x00b321d89a8c36b3929f20b7955080baed706d1b",
            yt_contract="../../etc/passwd",
            start_time_str="2023-01-01T00:00:00.000Z",
            network="ethereum"
        )
        self.assertIsNone(main.url_apy)
        self.assertIsNone(main.url_ohlcv_yteth)
        mock_st_error.assert_called_with("Invalid yield token contract address format.")

    @patch('streamlit.error')
    def test_main_with_valid_contracts(self, mock_st_error):
        market_contract = "0x00b321d89a8c36b3929f20b7955080baed706d1b"
        yt_contract = "0x4f0b4e6512630480b868e62a8a1d3451b0e9192d"
        main = Main(
            market_contract=market_contract,
            yt_contract=yt_contract,
            start_time_str="2023-01-01T00:00:00.000Z",
            network="ethereum"
        )
        self.assertEqual(
            main.url_apy,
            f"https://api-v2.pendle.finance/core/v1/1/markets/{market_contract}/apy-history-1ma"
        )
        self.assertEqual(
            main.url_ohlcv_yteth,
            f"https://api-v2.pendle.finance/core/v3/1/prices/{yt_contract}/ohlcv"
        )

    def test_fetch_methods_unsupported_network(self):
        m = object.__new__(Main)
        m.url_apy = None
        m.url_ohlcv_yteth = None

        df_ohlcv = m.fetch_yteth_ohlcv()
        self.assertTrue(df_ohlcv.empty)

        df_apy = m.fetch_apy()
        self.assertTrue(df_apy.empty)

def test_unsupported_network_stops_execution():
    with patch("streamlit.selectbox", return_value="invalid_network"), \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.stop", side_effect=RuntimeError("st.stop called")) as mock_stop:

        import pytest
        with pytest.raises(RuntimeError, match="st.stop called"):
            import importlib
            import ytTok
            importlib.reload(ytTok)

        mock_error.assert_called_with("Unsupported network type")
        mock_stop.assert_called_once()


def test_no_valid_assets_stops_execution():
    mock_response = MagicMock()
    mock_response.json.return_value = []

    st.cache_data.clear()
    with patch("streamlit.selectbox", return_value="ethereum"), \
         patch("requests.session") as mock_session_cls, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.stop", side_effect=RuntimeError("st.stop called")) as mock_stop:

        mock_session_inst = MagicMock()
        mock_session_inst.get.return_value = mock_response
        mock_session_cls.return_value = mock_session_inst

        import pytest
        with pytest.raises(RuntimeError, match="st.stop called"):
            import importlib
            import ytTok
            importlib.reload(ytTok)

        mock_error.assert_called_with("No valid assets found.")
        mock_stop.assert_called_once()

def test_add_purchase_time_annotation():
    fig = go.Figure()
    x_val = datetime(2024, 7, 25, 23, 0, 0)
    y_val = 100.5

    add_purchase_time_annotation(fig, x_val, y_val)

    # Verify vertical line shape was added
    assert len(fig.layout.shapes) == 1
    shape = fig.layout.shapes[0]
    assert shape.type == 'line'
    assert shape.x0 == x_val
    assert shape.x1 == x_val
    assert shape.line.color == 'green'
    assert shape.line.dash == 'dash'
    assert shape.line.width == 3

    # Verify annotation was added
    assert len(fig.layout.annotations) == 1
    annotation = fig.layout.annotations[0]
    assert annotation.x == x_val
    assert annotation.y == y_val
    assert annotation.text == "YT Purchase Time"
    assert annotation.showarrow is True
    assert annotation.arrowhead == 1
    assert annotation.ax == 20
    assert annotation.ay == -30

def test_add_purchase_time_annotation_custom_text():
    fig = go.Figure()
    x_val = "2024-07-25"
    y_val = 50
    custom_text = "Custom Annotation"

    add_purchase_time_annotation(fig, x_val, y_val, text=custom_text)

    assert len(fig.layout.annotations) == 1
    annotation = fig.layout.annotations[0]
    assert annotation.text == custom_text

class TestFetchApy:
    def setup_method(self):
        st.cache_data.clear()
        self.main_instance = Main(
            market_contract="0x00b321d89a8c36b3929f20b7955080baed706d1b",
            yt_contract="0x4f0b4e6512630480b868e62a8a1d3451b0e9192d",
            start_time_str="2023-01-01T00:00:00.000Z",
            network="ethereum"
        )
        self.main_instance.session = MagicMock()

    @patch('streamlit.error')
    def test_fetch_apy_success(self, mock_st_error):
        st.cache_data.clear()
        csv_data = "timestamp,impliedApy,underlyingApy\n1609459200,0.05,0.08\n1609462800,0.06,0.09\n"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": csv_data}
        self.main_instance.session.get.return_value = mock_response

        df = self.main_instance.fetch_apy()

        assert not df.empty
        assert len(df) == 2
        assert 'timestamp' in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])
        mock_st_error.assert_not_called()

    @patch('streamlit.error')
    def test_fetch_apy_no_results_key(self, mock_st_error):
        st.cache_data.clear()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_key": "data"}
        self.main_instance.session.get.return_value = mock_response

        df = self.main_instance.fetch_apy()

        assert df.empty
        mock_st_error.assert_called_once_with("No results found in the API response")

    @patch('streamlit.error')
    def test_fetch_apy_non_200_status_code(self, mock_st_error):
        st.cache_data.clear()
        mock_response = MagicMock()
        mock_response.status_code = 404
        self.main_instance.session.get.return_value = mock_response

        df = self.main_instance.fetch_apy()

        assert df.empty
        mock_st_error.assert_called_once_with("Failed to retrieve data with status code: 404")

    @patch('streamlit.error')
    def test_fetch_apy_server_error_500(self, mock_st_error):
        st.cache_data.clear()
        mock_response = MagicMock()
        mock_response.status_code = 500
        self.main_instance.session.get.return_value = mock_response

        df = self.main_instance.fetch_apy()

        assert df.empty
        mock_st_error.assert_called_once_with("Failed to retrieve data with status code: 500")

class MockResponse:
    def __init__(self, results):
        self._results = results
        self.status_code = 200
    def json(self):
        return {'results': self._results}

class MockSession:
    def __init__(self, results):
        self.results = results
    def get(self, url, headers=None, params=None):
        return MockResponse(self.results)

class TestOHLCV(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        self.main_obj = Main.__new__(Main)
        self.main_obj.url_ohlcv_yteth = "http://mock"
        self.main_obj.start_time_str = "2023-01-01T00:00:00.000Z"
        self.main_obj.end_time_str = "2023-01-02T00:00:00.000Z"

    def test_normal_data(self):
        st.cache_data.clear()
        results = [
            {'time': '2023-01-01T00:00:00.000Z', 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 100},
            {'time': '2023-01-01T01:00:00+00:00', 'open': 1.5, 'high': 2.5, 'low': 1.0, 'close': 2.0, 'volume': 200}
        ]
        self.main_obj.session = MockSession(results)
        df_opt = self.main_obj.fetch_yteth_ohlcv()
        self.assertEqual(len(df_opt), 2)
        self.assertListEqual(list(df_opt.columns), ['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.assertEqual(df_opt['Volume'].iloc[0], 100)

    def test_empty_results(self):
        st.cache_data.clear()
        results = []
        self.main_obj.session = MockSession(results)
        df_opt = self.main_obj.fetch_yteth_ohlcv()
        self.assertListEqual(list(df_opt.columns), ['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.assertTrue(df_opt.empty)

    def test_missing_volume_key(self):
        st.cache_data.clear()
        results = [
            {'time': '2023-01-01T00:00:00.000Z', 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5}
        ]
        self.main_obj.session = MockSession(results)
        df_opt = self.main_obj.fetch_yteth_ohlcv()
        self.assertEqual(df_opt['Volume'].iloc[0], 0)

    def test_none_volume_key(self):
        st.cache_data.clear()
        results = [
            {'time': '2023-01-01T00:00:00.000Z', 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': None}
        ]
        self.main_obj.session = MockSession(results)
        df_opt = self.main_obj.fetch_yteth_ohlcv()
        self.assertEqual(df_opt['Volume'].iloc[0], 0)

if __name__ == '__main__':
    unittest.main()
