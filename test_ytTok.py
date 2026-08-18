import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from ytTok import is_valid_address, Main

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

if __name__ == '__main__':
    unittest.main()
