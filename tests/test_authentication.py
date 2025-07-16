"""
Tests for API key authentication.

This module tests authentication behavior across all endpoints
to ensure proper security controls are in place.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os


class TestAuthentication:
    """Test cases for API key authentication across all endpoints."""

    @pytest.mark.parametrize(
        "endpoint,method,extra_headers",
        [
            ("/api/health", "GET", {}),
            ("/api/sessions", "POST", {}),
            ("/api/sessions/test-session", "GET", {}),
            ("/api/sessions/test-session", "DELETE", {}),
            ("/api/query", "POST", {"X-Session-ID": "test-session"}),
        ],
    )
    def test_valid_api_key_all_endpoints(
        self,
        client: TestClient,
        auth_headers,
        endpoint,
        method,
        extra_headers,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test that valid API key works for all endpoints."""
        headers = {**auth_headers, **extra_headers}

        if method == "GET":
            response = client.get(endpoint, headers=headers)
        elif method == "POST":
            json_data = {"message": "test"} if endpoint == "/api/query" else {}
            response = client.post(endpoint, headers=headers, json=json_data)
        elif method == "DELETE":
            response = client.delete(endpoint, headers=headers)

        # Should not get authentication errors
        assert response.status_code != 403
        assert response.status_code != 401

    @pytest.mark.parametrize(
        "endpoint,method,extra_headers",
        [
            ("/api/health", "GET", {}),
            ("/api/sessions", "POST", {}),
            ("/api/sessions/test-session", "GET", {}),
            ("/api/sessions/test-session", "DELETE", {}),
            ("/api/query", "POST", {"X-Session-ID": "test-session"}),
        ],
    )
    def test_invalid_api_key_all_endpoints(
        self, client: TestClient, endpoint, method, extra_headers
    ):
        """Test that invalid API key is rejected for all endpoints."""
        headers = {
            "Authorization": "Bearer invalid-api-key",
            "Content-Type": "application/json",
            **extra_headers,
        }

        if method == "GET":
            response = client.get(endpoint, headers=headers)
        elif method == "POST":
            json_data = {"message": "test"} if endpoint == "/api/query" else {}
            response = client.post(endpoint, headers=headers, json=json_data)
        elif method == "DELETE":
            response = client.delete(endpoint, headers=headers)

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

    @pytest.mark.parametrize(
        "endpoint,method,extra_headers",
        [
            ("/api/health", "GET", {}),
            ("/api/sessions", "POST", {}),
            ("/api/sessions/test-session", "GET", {}),
            ("/api/sessions/test-session", "DELETE", {}),
            ("/api/query", "POST", {"X-Session-ID": "test-session"}),
        ],
    )
    def test_missing_authorization_header_all_endpoints(
        self, client: TestClient, endpoint, method, extra_headers
    ):
        """Test that missing Authorization header is rejected for all endpoints."""
        headers = {"Content-Type": "application/json", **extra_headers}

        if method == "GET":
            response = client.get(endpoint, headers=headers)
        elif method == "POST":
            json_data = {"message": "test"} if endpoint == "/api/query" else {}
            response = client.post(endpoint, headers=headers, json=json_data)
        elif method == "DELETE":
            response = client.delete(endpoint, headers=headers)

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "auth_header_value",
        [
            "",  # Empty
            "Bearer",  # Missing token
            "Bearer ",  # Only Bearer with space
            "InvalidFormat test-api-key",  # Wrong format
            "test-api-key",  # Missing Bearer
            "bearer test-api-key",  # Wrong case
            "BEARER test-api-key",  # Wrong case
        ],
    )
    def test_malformed_authorization_headers(
        self, client: TestClient, auth_header_value
    ):
        """Test various malformed Authorization header formats."""
        headers = {
            "Authorization": auth_header_value,
            "Content-Type": "application/json",
        }

        response = client.get("/api/health", headers=headers)
        assert response.status_code == 403

    def test_api_key_case_sensitivity(self, client: TestClient, test_api_key):
        """Test that API key is case sensitive."""
        # Test with different case variations
        case_variations = [
            test_api_key.upper(),
            test_api_key.lower(),
            test_api_key.capitalize(),
            test_api_key.swapcase(),
        ]

        for variant in case_variations:
            if variant != test_api_key:  # Skip the correct one
                headers = {
                    "Authorization": f"Bearer {variant}",
                    "Content-Type": "application/json",
                }

                response = client.get("/api/health", headers=headers)
                assert response.status_code == 403

    def test_api_key_with_extra_whitespace(self, client: TestClient, test_api_key):
        """Test API key with extra whitespace."""
        whitespace_variations = [
            f" {test_api_key}",  # Leading space
            f"{test_api_key} ",  # Trailing space
            f" {test_api_key} ",  # Both
            f"{test_api_key}\t",  # Tab
            f"{test_api_key}\n",  # Newline
        ]

        for variant in whitespace_variations:
            headers = {
                "Authorization": f"Bearer {variant}",
                "Content-Type": "application/json",
            }

            response = client.get("/api/health", headers=headers)
            assert response.status_code == 403

    def test_multiple_authorization_headers(self, client: TestClient, test_api_key):
        """Test behavior with multiple Authorization headers."""
        # FastAPI/Starlette typically uses the first header, but this tests edge cases
        # Simulate multiple Authorization headers (this is implementation dependent)
        response = client.get(
            "/api/health",
            headers=[
                ("Authorization", f"Bearer {test_api_key}"),
                ("Authorization", "Bearer invalid-key"),
                ("Content-Type", "application/json"),
            ],
        )

        # The exact behavior may vary, but it should either work or fail securely
        assert response.status_code in [200, 403]

    def test_api_key_environment_variable_missing(
        self, client: TestClient, auth_headers
    ):
        """Test behavior when PP_API_KEY environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Create a new client without the mocked env vars
            from app.main import app

            temp_client = TestClient(app)

            response = temp_client.get("/api/health", headers=auth_headers)

            assert response.status_code == 500
            assert response.json() == {"detail": "PP_API_KEY not configured"}

    def test_api_key_environment_variable_empty(self, client: TestClient, auth_headers):
        """Test behavior when PP_API_KEY environment variable is empty."""
        with patch.dict(os.environ, {"PP_API_KEY": ""}, clear=True):
            from app.main import app

            temp_client = TestClient(app)

            response = temp_client.get("/api/health", headers=auth_headers)

            # Empty API key should be treated as not configured
            assert response.status_code in [403, 500]

    def test_very_long_api_key(self, client: TestClient):
        """Test behavior with very long API key."""
        very_long_key = "a" * 10000  # 10KB key
        headers = {
            "Authorization": f"Bearer {very_long_key}",
            "Content-Type": "application/json",
        }

        response = client.get("/api/health", headers=headers)

        # Should reject gracefully, not cause server errors
        assert response.status_code == 403
        assert "detail" in response.json()

    def test_api_key_with_special_characters(self, client: TestClient):
        """Test API key containing special characters."""
        special_keys = [
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key+with+plus",
            "key=with=equals",
            "key@with@at",
            "key#with#hash",
            "key%20with%20encoding",
        ]

        for special_key in special_keys:
            headers = {
                "Authorization": f"Bearer {special_key}",
                "Content-Type": "application/json",
            }

            response = client.get("/api/health", headers=headers)
            # All should be rejected since they're not the configured test key
            assert response.status_code == 403

    def test_concurrent_authentication_requests(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test concurrent requests with same API key."""
        import concurrent.futures

        def make_authenticated_request():
            return client.get("/api/health", headers=auth_headers)

        # Make 10 concurrent authenticated requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_authenticated_request) for _ in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All should succeed
        for response in responses:
            assert response.status_code == 200

    def test_authentication_performance(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test that authentication doesn't significantly impact response time."""
        import time

        # Make multiple requests and measure time
        times = []
        for _ in range(5):
            start_time = time.time()
            response = client.get("/api/health", headers=auth_headers)
            end_time = time.time()

            assert response.status_code == 200
            times.append(end_time - start_time)

        # Authentication should be fast (under 100ms for health check)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1  # 100ms

    def test_bearer_token_extraction(
        self, client: TestClient, test_api_key, mock_session_store
    ):
        """Test various formats of Bearer token extraction."""
        valid_formats = [
            f"Bearer {test_api_key}",
            f"Bearer  {test_api_key}",  # Extra space after Bearer
        ]

        for auth_format in valid_formats:
            headers = {"Authorization": auth_format, "Content-Type": "application/json"}

            response = client.get("/api/health", headers=headers)

            # Should work for properly formatted Bearer tokens
            if auth_format.strip() == f"Bearer {test_api_key}":
                assert response.status_code == 200
            else:
                # Extra spaces might be rejected depending on implementation
                assert response.status_code in [200, 403]

    def test_authentication_error_responses(self, client: TestClient):
        """Test that authentication errors return proper error responses."""
        test_cases = [
            ({"Authorization": "Bearer wrong-key"}, {"detail": "Invalid API key"}),
            ({}, None),  # No auth header - response varies by implementation
        ]

        for headers, expected_response in test_cases:
            headers.update({"Content-Type": "application/json"})
            response = client.get("/api/health", headers=headers)

            assert response.status_code == 403
            if expected_response:
                assert response.json() == expected_response

    def test_auth_header_injection_protection(self, client: TestClient, test_api_key):
        """Test protection against header injection attacks."""
        malicious_headers = [
            f"Bearer {test_api_key}\r\nX-Injected: malicious",
            f"Bearer {test_api_key}\nX-Injected: malicious",
            f"Bearer {test_api_key}; X-Injected: malicious",
        ]

        for malicious_header in malicious_headers:
            headers = {
                "Authorization": malicious_header,
                "Content-Type": "application/json",
            }

            response = client.get("/api/health", headers=headers)

            # Should reject malicious headers
            assert response.status_code == 403
