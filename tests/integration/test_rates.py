"""Integration tests for rates endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestLatestRatesEndpoint:
    """Tests for GET /rates/latest endpoint."""

    def test_returns_rates_success(self, client: TestClient, sample_rates_run: dict) -> None:
        """Successfully returns rates from repository."""
        response = client.get("/rates/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["base"] == "EUR"
        assert data["date"] == "2024-02-04"
        assert "rates" in data
        assert data["rates"]["USD"] == 1.0823

    def test_with_provider_param(self, client: TestClient, mock_rates_repo: MagicMock) -> None:
        """Uses specified provider parameter."""
        response = client.get("/rates/latest?provider=fixer")

        assert response.status_code == 200
        mock_rates_repo.get_latest_run.assert_called_with("fixer")

    def test_fallback_when_combined_not_found(
        self, client: TestClient, mock_rates_repo: MagicMock, sample_rates_run: dict
    ) -> None:
        """Falls back to individual providers when combined not found."""
        # First call (combined) returns None, second call (fixer) returns data
        mock_rates_repo.get_latest_run.side_effect = [None, sample_rates_run]

        response = client.get("/rates/latest")

        assert response.status_code == 200
        # Should have called combined first, then fixer fallback
        calls = mock_rates_repo.get_latest_run.call_args_list
        assert calls[0][0][0] == "combined"
        assert calls[1][0][0] == "fixer"

    def test_returns_404_when_no_rates(
        self, client: TestClient, mock_rates_repo: MagicMock
    ) -> None:
        """Returns 404 when no rates available from any provider."""
        mock_rates_repo.get_latest_run.return_value = None

        response = client.get("/rates/latest")

        assert response.status_code == 404
        assert response.json()["detail"] == "No rates available"

    def test_etag_caching_returns_304(self, client: TestClient, sample_rates_run: dict) -> None:
        """Returns 304 Not Modified when ETag matches."""
        # First request to get the ETag
        first_response = client.get("/rates/latest")
        etag = first_response.headers.get("ETag")

        # Second request with matching If-None-Match header
        second_response = client.get("/rates/latest", headers={"If-None-Match": etag})

        assert second_response.status_code == 304

    def test_includes_cache_headers(self, client: TestClient) -> None:
        """Response includes proper cache headers."""
        response = client.get("/rates/latest")

        assert "ETag" in response.headers
        assert "Cache-Control" in response.headers
        assert "max-age" in response.headers["Cache-Control"]

    def test_etag_format(self, client: TestClient) -> None:
        """ETag is properly formatted with quotes."""
        response = client.get("/rates/latest")
        etag = response.headers.get("ETag")

        assert etag is not None
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_different_provider_different_etag(
        self, client: TestClient, mock_rates_repo: MagicMock
    ) -> None:
        """Different providers produce different ETags."""
        # Setup different data for different providers
        combined_run = {
            "provider": "combined",
            "base": "EUR",
            "date": "2024-02-04",
            "fetched_at": "2024-02-04T12:00:00+00:00",
            "rates": {"USD": 1.08},
        }
        fixer_run = {
            "provider": "fixer",
            "base": "EUR",
            "date": "2024-02-04",
            "fetched_at": "2024-02-04T12:00:00+00:00",
            "rates": {"USD": 1.09},  # Different rate
        }

        mock_rates_repo.get_latest_run.return_value = combined_run
        response1 = client.get("/rates/latest")

        mock_rates_repo.get_latest_run.return_value = fixer_run
        response2 = client.get("/rates/latest?provider=fixer")

        assert response1.headers["ETag"] != response2.headers["ETag"]
