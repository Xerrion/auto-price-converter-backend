"""Tests for ProviderService."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.services.providers import ProviderService


class TestFetchFixer:
    """Tests for fetch_fixer method."""

    def test_success(self) -> None:
        """Successfully fetches and normalizes Fixer rates."""
        service = ProviderService(fixer_api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.0823, "GBP": 0.8543},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        result = service.fetch_fixer(mock_client)

        assert result is not None
        assert result["provider"] == "fixer"
        assert result["base"] == "EUR"
        assert result["date"] == "2024-02-04"
        assert "USD" in result["rates"]
        assert result["rates"]["EUR"] == 1.0

    def test_no_api_key_returns_none(self) -> None:
        """Returns None when no API key is configured."""
        service = ProviderService(fixer_api_key=None)

        mock_client = MagicMock(spec=httpx.Client)
        result = service.fetch_fixer(mock_client)

        assert result is None
        mock_client.get.assert_not_called()

    def test_api_error_raises_runtime_error(self) -> None:
        """Raises RuntimeError when Fixer API returns success=false."""
        service = ProviderService(fixer_api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": {"code": 101, "type": "invalid_access_key"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Fixer error"):
            service.fetch_fixer(mock_client)

    def test_http_error_propagates(self) -> None:
        """HTTP errors are propagated."""
        service = ProviderService(fixer_api_key="test-key")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service.fetch_fixer(mock_client)


class TestFetchFrankfurter:
    """Tests for fetch_frankfurter method."""

    def test_success(self) -> None:
        """Successfully fetches and normalizes Frankfurter rates."""
        service = ProviderService()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "base": "EUR",
            "date": "2024-02-04",
            "rates": {"USD": 1.0820, "JPY": 161.95},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        result = service.fetch_frankfurter(mock_client)

        assert result is not None
        assert result["provider"] == "frankfurter"
        assert result["base"] == "EUR"
        assert result["date"] == "2024-02-04"
        assert "USD" in result["rates"]
        assert "JPY" in result["rates"]
        assert result["rates"]["EUR"] == 1.0

    def test_http_error_propagates(self) -> None:
        """HTTP errors are propagated."""
        service = ProviderService()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service.fetch_frankfurter(mock_client)

    def test_unexpected_error_propagates(self) -> None:
        """Unexpected errors are logged and re-raised."""
        service = ProviderService()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = ValueError("Unexpected error")

        with pytest.raises(ValueError, match="Unexpected error"):
            service.fetch_frankfurter(mock_client)


class TestFetchFixerSymbols:
    """Tests for fetch_fixer_symbols method."""

    def test_success(self) -> None:
        """Successfully fetches Fixer symbols."""
        service = ProviderService(fixer_api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "symbols": {
                "EUR": "Euro",
                "USD": "United States Dollar",
                "GBP": "British Pound Sterling",
            },
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        result = service.fetch_fixer_symbols(mock_client)

        assert result is not None
        assert result["provider"] == "fixer"
        assert "EUR" in result["symbols"]
        assert result["symbols"]["EUR"] == "Euro"

    def test_no_api_key_returns_none(self) -> None:
        """Returns None when no API key is configured."""
        service = ProviderService(fixer_api_key=None)

        mock_client = MagicMock(spec=httpx.Client)
        result = service.fetch_fixer_symbols(mock_client)

        assert result is None
        mock_client.get.assert_not_called()

    def test_api_error_raises_runtime_error(self) -> None:
        """Raises RuntimeError when Fixer API returns success=false."""
        service = ProviderService(fixer_api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": {"code": 101, "type": "invalid_access_key"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Fixer symbols error"):
            service.fetch_fixer_symbols(mock_client)

    def test_unexpected_error_propagates(self) -> None:
        """Unexpected errors are logged and re-raised."""
        service = ProviderService(fixer_api_key="test-key")

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = ValueError("Unexpected symbols error")

        with pytest.raises(ValueError, match="Unexpected symbols error"):
            service.fetch_fixer_symbols(mock_client)
