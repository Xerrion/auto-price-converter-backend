"""Integration tests for symbols endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestLatestSymbolsEndpoint:
    """Tests for GET /symbols/latest endpoint."""

    def test_returns_symbols_success(self, client: TestClient, sample_symbols_run: dict) -> None:
        """Successfully returns symbols from repository."""
        response = client.get("/symbols/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "fixer"
        assert "symbols" in data
        assert data["symbols"]["EUR"] == "Euro"
        assert data["symbols"]["USD"] == "United States Dollar"

    def test_with_provider_param(self, client: TestClient, mock_symbols_repo: MagicMock) -> None:
        """Uses specified provider parameter."""
        client.get("/symbols/latest?provider=custom")

        mock_symbols_repo.get_latest.assert_called_with("custom")

    def test_returns_404_when_no_symbols(
        self, client: TestClient, mock_symbols_repo: MagicMock
    ) -> None:
        """Returns 404 when no symbols available."""
        mock_symbols_repo.get_latest.return_value = None

        response = client.get("/symbols/latest")

        assert response.status_code == 404
        assert response.json()["detail"] == "No symbols available"

    def test_etag_caching_returns_304(self, client: TestClient, sample_symbols_run: dict) -> None:
        """Returns 304 Not Modified when ETag matches."""
        # First request to get the ETag
        first_response = client.get("/symbols/latest")
        etag = first_response.headers.get("ETag")

        # Second request with matching If-None-Match header
        second_response = client.get("/symbols/latest", headers={"If-None-Match": etag})

        assert second_response.status_code == 304

    def test_includes_cache_headers(self, client: TestClient) -> None:
        """Response includes proper cache headers."""
        response = client.get("/symbols/latest")

        assert "ETag" in response.headers
        assert "Cache-Control" in response.headers
