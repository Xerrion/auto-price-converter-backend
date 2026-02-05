"""Integration tests for jobs endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestSyncEndpoint:
    """Tests for POST /jobs/sync endpoint."""

    def test_returns_401_without_api_key(self, client: TestClient) -> None:
        """Returns 401 Unauthorized when no API key provided."""
        response = client.post("/jobs/sync")

        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"

    def test_returns_401_with_invalid_key(self, client: TestClient) -> None:
        """Returns 401 Unauthorized with wrong API key."""
        response = client.post("/jobs/sync", headers={"X-API-Key": "wrong-key"})

        assert response.status_code == 401

    def test_sync_success_with_valid_key(
        self, client: TestClient, mock_sync_service: MagicMock
    ) -> None:
        """Successfully triggers sync with valid API key."""
        response = client.post("/jobs/sync", headers={"X-API-Key": "test-sync-key"})

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        mock_sync_service.sync_all_rates.assert_called_once_with(force=False)

    def test_sync_with_force_param(self, client: TestClient, mock_sync_service: MagicMock) -> None:
        """Force parameter is passed to sync service."""
        response = client.post("/jobs/sync?force=true", headers={"X-API-Key": "test-sync-key"})

        assert response.status_code == 200
        mock_sync_service.sync_all_rates.assert_called_once_with(force=True)

    def test_sync_returns_provider_results(
        self, client: TestClient, mock_sync_service: MagicMock
    ) -> None:
        """Returns results for each provider."""
        response = client.post("/jobs/sync", headers={"X-API-Key": "test-sync-key"})

        assert response.status_code == 200
        data = response.json()
        assert "fixer" in data["providers"]
        assert "frankfurter" in data["providers"]
        assert "combined" in data["providers"]
        assert "symbols" in data["providers"]

    def test_sync_run_id_in_response(
        self, client: TestClient, mock_sync_service: MagicMock
    ) -> None:
        """Run IDs are included in response."""
        response = client.post("/jobs/sync", headers={"X-API-Key": "test-sync-key"})

        assert response.status_code == 200
        data = response.json()
        assert data["providers"]["fixer"]["run_id"] == "fixer-run-id"
