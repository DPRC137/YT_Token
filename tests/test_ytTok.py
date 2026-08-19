import pytest
from unittest.mock import MagicMock, patch

def test_unsupported_network_stops_execution():
    with patch("streamlit.selectbox", return_value="invalid_network"), \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.stop", side_effect=RuntimeError("st.stop called")) as mock_stop:

        with pytest.raises(RuntimeError, match="st.stop called"):
            # Import or execute top-level code of ytTok in isolated context or module execution
            import importlib
            import ytTok
            importlib.reload(ytTok)

        mock_error.assert_called_with("Unsupported network type")
        mock_stop.assert_called_once()


def test_no_valid_assets_stops_execution():
    mock_response = MagicMock()
    mock_response.json.return_value = [] # Empty data returned

    with patch("streamlit.selectbox", return_value="ethereum"), \
         patch("requests.session") as mock_session_cls, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.stop", side_effect=RuntimeError("st.stop called")) as mock_stop:

        mock_session_inst = MagicMock()
        mock_session_inst.get.return_value = mock_response
        mock_session_cls.return_value = mock_session_inst

        with pytest.raises(RuntimeError, match="st.stop called"):
            import importlib
            import ytTok
            importlib.reload(ytTok)

        mock_error.assert_called_with("No valid assets found.")
        mock_stop.assert_called_once()
