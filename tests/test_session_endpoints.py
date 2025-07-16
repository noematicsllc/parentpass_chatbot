"""
Tests for session management endpoints.

This module tests the session creation, retrieval, and deletion endpoints
to ensure proper session management functionality and state handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from baml_client.types import State, Message


class TestSessionEndpoints:
    """Test cases for session management endpoints."""

    def test_create_session_success(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_uuid,
        test_session_id,
    ):
        """Test successful session creation."""
        # Configure mock session store
        mock_state = Mock(spec=State)
        mock_state.recent_messages = [
            Message(role="assistant", content="Welcome! How can I help you today?")
        ]
        mock_session_store.get_state.return_value = mock_state

        response = client.post("/api/sessions", headers=auth_headers)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "session_id" in data
        assert "state" in data
        assert data["session_id"] == test_session_id

        # Verify session store was called
        mock_session_store.get_state.assert_called_once_with(test_session_id)

    def test_create_session_no_auth(self, client: TestClient):
        """Test session creation without authentication."""
        response = client.post("/api/sessions")

        assert response.status_code == 403
        assert "detail" in response.json()

    def test_create_session_invalid_api_key(self, client: TestClient):
        """Test session creation with invalid API key."""
        headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
        }

        response = client.post("/api/sessions", headers=headers)

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

    def test_create_session_response_format(
        self, client: TestClient, auth_headers, mock_session_store, mock_uuid
    ):
        """Test that session creation returns correct response format."""
        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        response = client.post("/api/sessions", headers=auth_headers)

        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, dict)
        assert "session_id" in data
        assert "state" in data
        assert isinstance(data["session_id"], str)

    def test_get_session_success(
        self, client: TestClient, auth_headers, mock_session_store, test_session_id
    ):
        """Test successful session retrieval."""
        # Configure mock session store
        mock_state = Mock(spec=State)
        mock_state.recent_messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        mock_session_store.get_state.return_value = mock_state

        response = client.get(f"/api/sessions/{test_session_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "session_id" in data
        assert "state" in data
        assert data["session_id"] == test_session_id

        # Verify session store was called with correct session ID
        mock_session_store.get_state.assert_called_once_with(test_session_id)

    def test_get_session_no_auth(self, client: TestClient, test_session_id):
        """Test session retrieval without authentication."""
        response = client.get(f"/api/sessions/{test_session_id}")

        assert response.status_code == 403
        assert "detail" in response.json()

    def test_get_session_invalid_api_key(self, client: TestClient, test_session_id):
        """Test session retrieval with invalid API key."""
        headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
        }

        response = client.get(f"/api/sessions/{test_session_id}", headers=headers)

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

    def test_get_nonexistent_session(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test retrieving a non-existent session."""
        # Configure mock to return empty state for non-existent session
        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        nonexistent_id = "nonexistent-session-id"
        response = client.get(f"/api/sessions/{nonexistent_id}", headers=auth_headers)

        assert (
            response.status_code == 200
        )  # Session store creates new state if not found
        data = response.json()
        assert data["session_id"] == nonexistent_id

    def test_get_session_special_characters(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test session retrieval with special characters in session ID."""
        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # Test with URL-encoded special characters
        special_session_id = "session-with-special%20chars"
        response = client.get(
            f"/api/sessions/{special_session_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # FastAPI automatically decodes URL-encoded characters
        expected_session_id = "session-with-special chars"
        assert data["session_id"] == expected_session_id

    def test_delete_session_success(
        self, client: TestClient, auth_headers, mock_session_store, test_session_id
    ):
        """Test successful session deletion."""
        response = client.delete(
            f"/api/sessions/{test_session_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "deleted" in data
        assert data["deleted"] is True
        assert "session_id" in data
        assert data["session_id"] == test_session_id
        assert "timestamp" in data

        # Verify session store delete was called
        mock_session_store.delete_session.assert_called_once_with(test_session_id)

    def test_delete_session_no_auth(self, client: TestClient, test_session_id):
        """Test session deletion without authentication."""
        response = client.delete(f"/api/sessions/{test_session_id}")

        assert response.status_code == 403
        assert "detail" in response.json()

    def test_delete_session_invalid_api_key(self, client: TestClient, test_session_id):
        """Test session deletion with invalid API key."""
        headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
        }

        response = client.delete(f"/api/sessions/{test_session_id}", headers=headers)

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

    def test_delete_nonexistent_session(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test deleting a non-existent session."""
        nonexistent_id = "nonexistent-session-id"
        response = client.delete(
            f"/api/sessions/{nonexistent_id}", headers=auth_headers
        )

        assert (
            response.status_code == 200
        )  # Should succeed even if session doesn't exist
        data = response.json()
        assert data["deleted"] is True
        assert "session_id" in data
        assert data["session_id"] == nonexistent_id
        assert "timestamp" in data

        # Verify delete was called
        mock_session_store.delete_session.assert_called_once_with(nonexistent_id)

    def test_session_endpoints_http_methods(
        self,
        client: TestClient,
        auth_headers,
        test_session_id,
        mock_session_store,
        mock_uuid,
    ):
        """Test that session endpoints only accept appropriate HTTP methods."""
        # Test POST /api/sessions (should work)
        response = client.post("/api/sessions", headers=auth_headers)
        assert response.status_code == 201

        # Test GET /api/sessions/{id} (should work)
        response = client.get(f"/api/sessions/{test_session_id}", headers=auth_headers)
        assert response.status_code == 200

        # Test DELETE /api/sessions/{id} (should work)
        response = client.delete(
            f"/api/sessions/{test_session_id}", headers=auth_headers
        )
        assert response.status_code == 200

        # Test invalid methods
        response = client.put(f"/api/sessions/{test_session_id}", headers=auth_headers)
        assert response.status_code == 405  # Method Not Allowed

        response = client.patch(
            f"/api/sessions/{test_session_id}", headers=auth_headers
        )
        assert response.status_code == 405

    def test_session_lifecycle(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_uuid,
        test_session_id,
    ):
        """Test complete session lifecycle: create -> get -> delete."""
        # Configure mock for session creation
        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # 1. Create session
        create_response = client.post("/api/sessions", headers=auth_headers)
        assert create_response.status_code == 201
        session_data = create_response.json()
        session_id = session_data["session_id"]

        # 2. Get session
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["session_id"] == session_id

        # 3. Delete session
        delete_response = client.delete(
            f"/api/sessions/{session_id}", headers=auth_headers
        )
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["deleted"] is True
        assert "session_id" in delete_data
        assert delete_data["session_id"] == session_id
        assert "timestamp" in delete_data

    @pytest.mark.parametrize(
        "session_id",
        [
            "simple-session-id",
            "session_with_underscores",
            "session-with-dashes",
            "SessionWithCapitals",
            "123456789",
            "mix3d-Ch4r5_AND_numb3rs",
        ],
    )
    def test_session_id_formats(
        self, client: TestClient, auth_headers, mock_session_store, session_id
    ):
        """Test various session ID formats."""
        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        # Test get and delete with different session ID formats
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_response.status_code == 200

        delete_response = client.delete(
            f"/api/sessions/{session_id}", headers=auth_headers
        )
        assert delete_response.status_code == 200

    def test_concurrent_session_operations(
        self, client: TestClient, auth_headers, mock_session_store
    ):
        """Test concurrent session operations."""
        import concurrent.futures

        mock_state = Mock(spec=State)
        mock_state.recent_messages = []
        mock_session_store.get_state.return_value = mock_state

        def create_session():
            with patch("app.routers.sessions.uuid.uuid4") as mock_uuid4:
                mock_uuid4.return_value = Mock()
                mock_uuid4.return_value.__str__ = Mock(
                    return_value=f"concurrent-session-{id(mock_uuid4)}"
                )
                return client.post("/api/sessions", headers=auth_headers)

        # Create 5 sessions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session) for _ in range(5)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All sessions should be created successfully
        for response in responses:
            assert response.status_code == 201
            data = response.json()
            assert "session_id" in data
            assert "state" in data
