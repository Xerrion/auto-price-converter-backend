"""Integration tests for health endpoint."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """GET /health returns status ok."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_content_type(self, client: TestClient) -> None:
        """GET /health returns JSON content type."""
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"
