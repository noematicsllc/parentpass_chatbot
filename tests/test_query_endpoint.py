"""
Tests for the /api/query endpoint.

This module tests the main chatbot query functionality including
BAML integration, analytics data loading, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from baml_client.types import Message, State, AnalyticsQuestion, AnalyticsCategory


class TestQueryEndpoint:
    """Test cases for the /api/query endpoint."""

    def test_query_success_direct_message(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test successful query with direct message response from BAML."""
        # Configure mocks - use a real State object that can be modified
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Mock BAML client to return a direct message
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert data["response"] == sample_message.content
        assert "session_id" in data
        assert "timestamp" in data
        assert "processing_time_ms" in data

        # Verify BAML client was called
        mock_baml_client.Chat.assert_called_once()

        # Verify messages were added to state
        assert len(mock_state.recent_messages) == 2  # User message + assistant response

    def test_query_success_analytics_question(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        mock_analytics_loader,
        sample_analytics_question,
        sample_message,
    ):
        """Test successful query with analytics question response."""
        # Configure mocks - use a real State object that can be modified
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Mock BAML client to return analytics question first, then answer
        mock_baml_client.Chat = AsyncMock(return_value=sample_analytics_question)
        mock_baml_client.AnswerAnalyticsQuestion = AsyncMock(
            return_value=sample_message
        )

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["response"] == sample_message.content

        # Verify all components were called
        mock_baml_client.Chat.assert_called_once()
        mock_analytics_loader.assert_called_once_with(AnalyticsCategory.USERS)
        mock_baml_client.AnswerAnalyticsQuestion.assert_called_once()

    def test_query_analytics_no_data(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        mock_analytics_loader,
        sample_analytics_question,
    ):
        """Test query when analytics data is not available."""
        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Mock BAML to return analytics question
        mock_baml_client.Chat = AsyncMock(return_value=sample_analytics_question)

        # Mock analytics loader to return None (no data)
        mock_analytics_loader.return_value = None

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Should get the fallback message
        assert "analytics data needed" in data["response"].lower()

        # Verify calls
        mock_baml_client.Chat.assert_called_once()
        mock_analytics_loader.assert_called_once_with(AnalyticsCategory.USERS)

    def test_query_unexpected_response_type(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
    ):
        """Test query when BAML returns unexpected response type."""
        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Mock BAML to return unexpected type
        mock_baml_client.Chat = AsyncMock(return_value="unexpected_string")

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Should get the fallback message
        assert "having trouble processing" in data["response"].lower()

        # Verify BAML was called
        mock_baml_client.Chat.assert_called_once()

    def test_query_without_session_header(
        self, client: TestClient, auth_headers, valid_query_payload
    ):
        """Test query without X-Session-ID header."""
        response = client.post(
            "/api/query", headers=auth_headers, json=valid_query_payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "session" in data["detail"].lower()

    def test_query_invalid_session_header(
        self, client: TestClient, auth_headers, valid_query_payload
    ):
        """Test query with invalid X-Session-ID header."""
        headers = {**auth_headers, "X-Session-ID": ""}

        response = client.post("/api/query", headers=headers, json=valid_query_payload)

        assert response.status_code == 400
        data = response.json()
        assert "session" in data["detail"].lower()

    def test_query_missing_message(self, client: TestClient, session_headers):
        """Test query with missing message field."""
        payload = {}

        response = client.post("/api/query", headers=session_headers, json=payload)

        assert response.status_code == 422  # Validation error

    def test_query_empty_message(self, client: TestClient, session_headers):
        """Test query with empty message field."""
        payload = {"message": ""}

        # Since the API doesn't validate empty strings as errors, test should pass
        # But we need to mock the session store to avoid errors
        with patch("app.routers.queries.session_store") as mock_store, \
             patch("app.routers.queries.b") as mock_baml:
            mock_state = State(recent_messages=[])
            mock_store.get_state.return_value = mock_state
            mock_baml.Chat = AsyncMock(return_value=Message(role="assistant", content="response"))
            
            response = client.post("/api/query", headers=session_headers, json=payload)
            assert response.status_code == 200  # Empty messages are allowed

    def test_query_non_string_message(self, client: TestClient, session_headers):
        """Test query with non-string message field."""
        payload = {"message": 123}

        response = client.post("/api/query", headers=session_headers, json=payload)

        assert response.status_code == 422  # Validation error

    def test_query_no_auth(self, client: TestClient, valid_query_payload):
        """Test query without authentication."""
        headers = {"Content-Type": "application/json", "X-Session-ID": "test-session"}

        response = client.post("/api/query", headers=headers, json=valid_query_payload)

        assert response.status_code == 403

    def test_query_invalid_auth(self, client: TestClient, valid_query_payload):
        """Test query with invalid authentication."""
        headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
            "X-Session-ID": "test-session",
        }

        response = client.post("/api/query", headers=headers, json=valid_query_payload)

        assert response.status_code == 403

    def test_query_baml_error_handling(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
    ):
        """Test query when BAML client raises an exception."""
        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Mock BAML to raise an exception
        mock_baml_client.Chat = AsyncMock(side_effect=Exception("BAML error"))

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        # The app gracefully handles BAML errors and returns a 200 with error message
        assert response.status_code == 200
        data = response.json()
        assert "having trouble processing" in data["response"].lower()

    def test_query_special_characters(
        self,
        client: TestClient,
        session_headers,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test query with special characters in message."""
        special_message = "Hello! 🤖 This has émojis, ñ, and 中文 characters."
        payload = {"message": special_message}

        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        response = client.post("/api/query", headers=session_headers, json=payload)

        assert response.status_code == 200

        # Verify the special character message was added to state
        user_message = mock_state.recent_messages[0]
        assert user_message.content == special_message
        assert user_message.role == "user"

    def test_query_state_management(
        self,
        client: TestClient,
        session_headers,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test that query properly manages conversation state."""
        # Configure mocks
        existing_messages = [
            Message(role="assistant", content="Welcome!"),
            Message(role="user", content="Previous question"),
            Message(role="assistant", content="Previous answer"),
        ]
        mock_state = State(recent_messages=existing_messages.copy())
        mock_session_store.sync_state(mock_state)
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        payload = {"message": "New question"}
        response = client.post("/api/query", headers=session_headers, json=payload)

        assert response.status_code == 200

        # Verify state now has original messages plus new user message and response
        assert len(mock_state.recent_messages) == 5

        # Check the last two messages
        user_msg = mock_state.recent_messages[-2]
        assistant_msg = mock_state.recent_messages[-1]

        assert user_msg.role == "user"
        assert user_msg.content == "New question"
        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == sample_message.content

    def test_query_http_methods(
        self, client: TestClient, session_headers, valid_query_payload
    ):
        """Test that query endpoint only accepts POST requests."""
        # Test POST (should work)
        with patch("app.routers.queries.session_store"), patch("app.routers.queries.b"):
            response = client.post(
                "/api/query", headers=session_headers, json=valid_query_payload
            )
            # Don't check exact status since mocks aren't configured
            assert response.status_code in [200, 500]  # Either works or fails due to mocks

        # Test GET (should fail)
        response = client.get("/api/query", headers=session_headers)
        assert response.status_code == 405  # Method not allowed

        # Test PUT (should fail)
        response = client.put(
            "/api/query", headers=session_headers, json=valid_query_payload
        )
        assert response.status_code == 405

        # Test DELETE (should fail)
        response = client.delete("/api/query", headers=session_headers)
        assert response.status_code == 405

    def test_query_processing_time(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test that query response includes processing time."""
        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )

        assert response.status_code == 200
        data = response.json()

        # Verify processing time is included and reasonable
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)
        assert data["processing_time_ms"] >= 0
        assert data["processing_time_ms"] < 10000  # Should be less than 10 seconds

    def test_query_response_timestamp(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test that query response includes timestamp."""
        import datetime

        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        before_request = datetime.datetime.now()
        response = client.post(
            "/api/query", headers=session_headers, json=valid_query_payload
        )
        after_request = datetime.datetime.now()

        assert response.status_code == 200
        data = response.json()

        # Verify timestamp is included and reasonable
        assert "timestamp" in data
        timestamp_str = data["timestamp"]
        timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Timestamp should be between request start and end (with some tolerance)
        assert (timestamp.replace(tzinfo=None) - before_request).total_seconds() >= -1
        assert (after_request - timestamp.replace(tzinfo=None)).total_seconds() >= -1

    def test_query_large_message(
        self,
        client: TestClient,
        session_headers,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test query with very large message."""
        # Create a large message (but not too large to avoid test slowness)
        large_message = "This is a test message. " * 1000  # About 25KB
        payload = {"message": large_message}

        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)
        mock_baml_client.Chat = AsyncMock(return_value=sample_message)

        response = client.post("/api/query", headers=session_headers, json=payload)

        assert response.status_code == 200

        # Verify the large message was handled correctly
        user_message = mock_state.recent_messages[0]
        assert user_message.content == large_message
        assert len(user_message.content) > 20000

    def test_query_concurrent_requests(
        self,
        client: TestClient,
        session_headers,
        valid_query_payload,
        mock_session_store,
        mock_baml_client,
        sample_message,
    ):
        """Test concurrent query requests to the same session."""
        import concurrent.futures
        import time
        import asyncio

        # Configure mocks
        mock_state = State(recent_messages=[])
        mock_session_store.sync_state(mock_state)

        # Add a small delay to BAML response to simulate real processing
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Small delay
            return sample_message

        mock_baml_client.Chat = AsyncMock(side_effect=delayed_response)

        def make_request():
            return client.post(
                "/api/query", headers=session_headers, json=valid_query_payload
            )

        # Make 3 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # The session state should have been updated multiple times
        # (6 messages: 3 user + 3 assistant)
        assert len(mock_state.recent_messages) >= 6
