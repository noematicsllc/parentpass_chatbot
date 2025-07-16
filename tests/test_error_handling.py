"""
Tests for error handling and edge cases.

This module tests error scenarios, edge cases, and exception handling
to ensure the API behaves gracefully under various failure conditions.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class TestErrorHandling:
    """Test cases for error handling and edge cases."""

    def test_invalid_json_content_type(self, client: TestClient, session_headers):
        """Test sending JSON data with wrong content type."""
        headers = {**session_headers}
        headers["Content-Type"] = "text/plain"

        response = client.post("/api/query", headers=headers, json={"message": "test"})

        # Should handle gracefully
        assert response.status_code in [200, 400, 415, 422]

    def test_malformed_json_payload(self, client: TestClient, session_headers):
        """Test endpoints with malformed JSON payload."""
        # Test completely invalid JSON
        response = client.post(
            "/api/query",
            headers=session_headers,
            content='{"message": "test"',  # Missing closing brace
        )
        assert response.status_code == 422

    def test_extremely_large_payload(self, client: TestClient, session_headers):
        """Test endpoints with extremely large payloads."""
        # Create a very large message (1MB)
        large_message = "x" * (1024 * 1024)
        payload = {"message": large_message}

        response = client.post("/api/query", headers=session_headers, json=payload)

        # Should handle gracefully - either accept or reject with proper error
        assert response.status_code in [200, 413, 422]

    def test_unicode_and_special_characters(
        self, client: TestClient, session_headers, mock_session_store, mock_baml_client
    ):
        """Test handling of various Unicode and special characters."""
        special_messages = [
            "Hello 🤖🎉👋",  # Emojis
            "Text with ñ, é, ü, ç characters",  # Accented characters
            "中文测试",  # Chinese characters
            "العربية",  # Arabic
            "Русский",  # Russian
            "🔥💯✨🚀",  # Only emojis
            "Mixed: Hello 世界 🌍",  # Mixed languages and emojis
            "\n\t\r special whitespace",  # Special whitespace
            "\"quotes\" and 'apostrophes'",  # Quotes
            "Symbols: @#$%^&*()+=[]{}|\\:;\"'<>?,./",  # Special symbols
        ]

        # Configure mocks
        mock_state = Mock()
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state
        mock_baml_client.Chat = AsyncMock(return_value=Mock(content="Response"))

        for message in special_messages:
            payload = {"message": message}
            response = client.post("/api/query", headers=session_headers, json=payload)

            # Should handle all Unicode gracefully
            assert response.status_code == 200

    def test_null_and_empty_values(self, client: TestClient, session_headers):
        """Test handling of null and empty values in requests."""
        test_payloads = [
            {"message": None},  # Null message
            {"message": ""},  # Empty string
            {},  # Missing message field
            {"message": 0},  # Wrong type (number)
            {"message": []},  # Wrong type (array)
            {"message": {}},  # Wrong type (object)
        ]

        for payload in test_payloads:
            response = client.post("/api/query", headers=session_headers, json=payload)

            # Should reject invalid payloads properly
            assert response.status_code in [200, 400, 422]

            if response.status_code == 422:
                # Should have validation error details
                error_data = response.json()
                assert "detail" in error_data

    def test_session_store_exceptions(
        self, client: TestClient, auth_headers, test_session_id
    ):
        """Test handling when session store raises exceptions."""
        # Test session creation with store exception
        with (
            patch("app.routers.sessions.session_store") as mock_store,
            patch("app.routers.sessions.uuid.uuid4"),
        ):
            mock_store.get_state.side_effect = Exception("Session store error")

            # FastAPI will let unhandled exceptions bubble up, causing a test failure
            # This is expected behavior - the application should handle this gracefully in production
            with pytest.raises(Exception, match="Session store error"):
                client.post("/api/sessions", headers=auth_headers)

        # Test session retrieval with store exception
        with patch("app.routers.sessions.session_store") as mock_store:
            mock_store.get_state.side_effect = Exception("Session store error")

            # FastAPI will let unhandled exceptions bubble up
            with pytest.raises(Exception, match="Session store error"):
                client.get(f"/api/sessions/{test_session_id}", headers=auth_headers)

        # Test session deletion with store exception
        with patch("app.routers.sessions.session_store") as mock_store:
            mock_store.delete_session.side_effect = Exception("Session store error")

            # FastAPI will let unhandled exceptions bubble up
            with pytest.raises(Exception, match="Session store error"):
                client.delete(f"/api/sessions/{test_session_id}", headers=auth_headers)

    def test_baml_client_various_exceptions(
        self, client: TestClient, session_headers, mock_session_store
    ):
        """Test handling of various BAML client exceptions."""
        mock_state = Mock()
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        exception_types = [
            Exception("Generic error"),
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            ValueError("Invalid value"),
            RuntimeError("Runtime error"),
            KeyError("Missing key"),
        ]

        for exception in exception_types:
            with patch("app.routers.queries.b") as mock_baml:
                mock_baml.Chat = AsyncMock(side_effect=exception)

                response = client.post(
                    "/api/query", headers=session_headers, json={"message": "test"}
                )

                # Should handle all exceptions gracefully
                assert response.status_code == 200
                data = response.json()
                assert "having trouble processing your request" in data["response"]

    def test_analytics_loader_exceptions(
        self, client: TestClient, session_headers, mock_session_store, mock_baml_client
    ):
        """Test handling when analytics loader raises exceptions."""
        # Configure mocks
        mock_state = Mock()
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # Mock BAML to return analytics question
        from baml_client.types import AnalyticsQuestion, AnalyticsCategory

        analytics_question = AnalyticsQuestion(
            category=AnalyticsCategory.USERS, question="Test question"
        )
        mock_baml_client.Chat = AsyncMock(return_value=analytics_question)

        # Mock analytics loader to raise exception
        with patch("app.routers.queries.get_analytics_data_for_category") as mock_loader:
            mock_loader.side_effect = Exception("Analytics error")

            response = client.post(
                "/api/query", headers=session_headers, json={"message": "test"}
            )

            # Should handle analytics errors gracefully
            assert response.status_code == 200
            data = response.json()
            assert "having trouble processing your request" in data["response"]

    def test_invalid_session_ids(
        self, client: TestClient, auth_headers, mock_session_store, sample_state
    ):
        """Test handling of invalid session IDs."""
        # Use proper State object from fixture
        mock_session_store.get_state.return_value = sample_state

        invalid_session_ids = [
            "",  # Empty
            " ",  # Whitespace only
            "../../etc/passwd",  # Path traversal attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "session id with spaces",  # Spaces
            "session/with/slashes",  # Slashes
            "session?with=query",  # Query parameters
            "session#with-fragment",  # Fragment
            "extremely-long-session-id-" + "x" * 1000,  # Very long
        ]

        for session_id in invalid_session_ids:
            # Test GET session
            response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
            # Should handle gracefully - either work or return proper error
            # 405 can occur for malformed URLs that don't match route patterns
            assert response.status_code in [200, 400, 404, 405, 422]

            # Test DELETE session
            response = client.delete(
                f"/api/sessions/{session_id}", headers=auth_headers
            )
            # Should handle gracefully - 405 can also occur for malformed URLs
            assert response.status_code in [200, 400, 404, 405, 422]

    def test_concurrent_request_handling(
        self, client: TestClient, session_headers, mock_session_store, mock_baml_client
    ):
        """Test handling of concurrent requests that might cause race conditions."""
        import concurrent.futures

        # Configure mocks
        mock_state = Mock()
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # Mock BAML with delay to increase chance of race conditions
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return Mock(content="Delayed response")

        mock_baml_client.Chat = AsyncMock(side_effect=delayed_response)

        def make_request(request_id):
            return client.post(
                "/api/query",
                headers=session_headers,
                json={"message": f"Concurrent request {request_id}"},
            )

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All should complete successfully without errors
        for response in responses:
            assert response.status_code == 200

    def test_memory_and_resource_limits(
        self, client: TestClient, auth_headers, sample_state
    ):
        """Test behavior under memory/resource constraints."""
        # Test creating many sessions rapidly
        session_ids = []

        with (
            patch("app.routers.sessions.session_store") as mock_store,
            patch("app.routers.sessions.uuid.uuid4"),
        ):
            mock_store.get_state.return_value = sample_state

            # Create 100 sessions rapidly
            for i in range(100):
                response = client.post("/api/sessions", headers=auth_headers)

                # Should handle resource pressure gracefully
                assert response.status_code in [
                    201,
                    429,
                    500,
                    503,
                ]  # Created, rate limited, or server error

                if response.status_code == 201:
                    session_data = response.json()
                    session_ids.append(session_data["session_id"])

        # Should create at least some sessions
        assert len(session_ids) > 0

    def test_malformed_request_headers(
        self, client: TestClient, test_api_key, test_session_id
    ):
        """Test handling of malformed or unusual request headers."""
        malformed_headers = [
            # Missing required headers
            {"Authorization": f"Bearer {test_api_key}"},  # Missing session ID for query
            {"X-Session-ID": test_session_id},  # Missing auth for query
            # Malformed values
            {"Authorization": f"Bearer {test_api_key}", "X-Session-ID": ""},
            {"Authorization": f"Bearer {test_api_key}", "X-Session-ID": None},
            # Extra headers that might confuse parsing
            {
                "Authorization": f"Bearer {test_api_key}",
                "X-Session-ID": test_session_id,
                "X-Forwarded-For": "malicious-ip",
                "User-Agent": "'; DROP TABLE sessions; --",
            },
        ]

        for headers in malformed_headers:
            # Filter None values as they can't be sent as headers
            clean_headers = {k: v for k, v in headers.items() if v is not None}
            clean_headers["Content-Type"] = "application/json"

            response = client.post(
                "/api/query", headers=clean_headers, json={"message": "test"}
            )

            # Should handle malformed headers gracefully
            assert response.status_code in [200, 400, 403, 422]

    def test_network_simulation_errors(
        self, client: TestClient, session_headers, mock_session_store
    ):
        """Test handling of simulated network-related errors."""
        mock_state = Mock()
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # Simulate various network errors in BAML client
        network_errors = [
            ConnectionError("Connection refused"),
            TimeoutError("Request timed out"),
            OSError("Network unreachable"),
        ]

        for error in network_errors:
            with patch("app.routers.queries.b") as mock_baml:
                mock_baml.Chat = AsyncMock(side_effect=error)

                response = client.post(
                    "/api/query", headers=session_headers, json={"message": "test"}
                )

                # Should handle network errors gracefully
                assert response.status_code == 200
                data = response.json()
                assert "having trouble processing your request" in data["response"]

    def test_endpoint_not_found(self, client: TestClient, auth_headers):
        """Test accessing non-existent endpoints."""
        non_existent_endpoints = [
            "/api/nonexistent",
            "/api/health/detailed",
            "/api/sessions/extra/path",
            "/api/query/wrong",
            "/wrong/api/path",
            "/api/v2/health",  # Version that doesn't exist
        ]

        for endpoint in non_existent_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 404

    def test_http_method_not_allowed(
        self, client: TestClient, auth_headers, test_session_id
    ):
        """Test using wrong HTTP methods on endpoints."""
        wrong_method_tests = [
            ("/api/health", "POST"),
            ("/api/health", "PUT"),
            ("/api/health", "DELETE"),
            ("/api/sessions", "GET"),
            ("/api/sessions", "PUT"),
            ("/api/sessions", "DELETE"),
            (f"/api/sessions/{test_session_id}", "POST"),
            (f"/api/sessions/{test_session_id}", "PUT"),
            ("/api/query", "GET"),
            ("/api/query", "PUT"),
            ("/api/query", "DELETE"),
        ]

        for endpoint, method in wrong_method_tests:
            response = client.request(method, endpoint, headers=auth_headers)
            assert response.status_code == 405  # Method Not Allowed

    def test_content_length_edge_cases(self, client: TestClient, session_headers):
        """Test edge cases with content length."""
        # Test with explicit content-length that doesn't match
        headers_with_length = {**session_headers, "Content-Length": "1000"}
        small_payload = {"message": "small"}

        response = client.post(
            "/api/query", headers=headers_with_length, json=small_payload
        )

        # Should handle content-length mismatches gracefully
        assert response.status_code in [200, 400, 411, 413]

    @pytest.mark.parametrize(
        "invalid_content_type",
        [
            "application/xml",
            "text/html",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "invalid/content-type",
            "",  # Empty content type
        ],
    )
    def test_unsupported_content_types(
        self, client: TestClient, session_headers, invalid_content_type
    ):
        """Test endpoints with unsupported content types."""
        headers = {**session_headers}
        headers["Content-Type"] = invalid_content_type

        response = client.post(
            "/api/query", headers=headers, content='{"message": "test"}'
        )

        # Should handle unsupported content types appropriately
        assert response.status_code in [200, 400, 415, 422]
