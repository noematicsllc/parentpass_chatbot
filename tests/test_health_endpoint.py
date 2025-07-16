"""
Tests for the /api/health endpoint.

This module tests the health check functionality to ensure the API
is responding correctly and authentication is working as expected.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestHealthEndpoint:
    """Test cases for the /api/health endpoint."""

    def test_health_check_success(self, client: TestClient, auth_headers):
        """Test successful health check with valid API key."""
        response = client.get("/api/health", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_health_check_no_auth_header(self, client: TestClient):
        """Test health check without Authorization header."""
        response = client.get("/api/health")

        assert response.status_code == 403
        assert "detail" in response.json()

    def test_health_check_invalid_api_key(self, client: TestClient):
        """Test health check with invalid API key."""
        headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
        }

        response = client.get("/api/health", headers=headers)

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

    def test_health_check_malformed_auth_header(self, client: TestClient):
        """Test health check with malformed Authorization header."""
        headers = {
            "Authorization": "InvalidFormat test-api-key",
            "Content-Type": "application/json",
        }

        response = client.get("/api/health", headers=headers)

        assert response.status_code == 403

    def test_health_check_missing_bearer(self, client: TestClient):
        """Test health check with missing Bearer prefix."""
        headers = {"Authorization": "test-api-key", "Content-Type": "application/json"}

        response = client.get("/api/health", headers=headers)

        assert response.status_code == 403

    def test_health_check_empty_auth_header(self, client: TestClient):
        """Test health check with empty Authorization header."""
        headers = {"Authorization": "", "Content-Type": "application/json"}

        response = client.get("/api/health", headers=headers)

        assert response.status_code == 403

    def test_health_check_no_env_api_key(self, client: TestClient, auth_headers):
        """Test health check when PP_API_KEY environment variable is not set."""
        with patch.dict("os.environ", {}, clear=True):
            # Create a new client without the mocked env vars
            from app.main import app

            temp_client = TestClient(app)

            response = temp_client.get("/api/health", headers=auth_headers)

            assert response.status_code == 500
            assert response.json() == {"detail": "PP_API_KEY not configured"}

    def test_health_check_http_methods(self, client: TestClient, auth_headers):
        """Test that health endpoint only accepts GET requests."""
        # Test GET (should work)
        response = client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200

        # Test POST (should not be allowed)
        response = client.post("/api/health", headers=auth_headers)
        assert response.status_code == 405  # Method Not Allowed

        # Test PUT (should not be allowed)
        response = client.put("/api/health", headers=auth_headers)
        assert response.status_code == 405

        # Test DELETE (should not be allowed)
        response = client.delete("/api/health", headers=auth_headers)
        assert response.status_code == 405

    def test_health_check_response_format(self, client: TestClient, auth_headers):
        """Test that health check returns correct response format."""
        response = client.get("/api/health", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

        # Ensure expected fields are returned
        expected_fields = {"status", "timestamp", "version"}
        assert set(data.keys()) == expected_fields

    def test_health_check_concurrent_requests(self, client: TestClient, auth_headers):
        """Test health endpoint under concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/api/health", headers=auth_headers)

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
            assert data["version"] == "1.0.0"

    @pytest.mark.parametrize("method", ["GET", "get", "Get"])
    def test_health_check_case_insensitive_method(
        self, client: TestClient, auth_headers, method
    ):
        """Test that health endpoint works with different case GET methods."""
        response = client.request(method.upper(), "/api/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
