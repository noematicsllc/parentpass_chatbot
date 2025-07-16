"""
pytest configuration and fixtures for ParentPass Chatbot API tests.
This file contains shared fixtures for testing the API endpoints
and ensures consistent test setup across all test modules.
"""

import os
import asyncio
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.main import app
from baml_client.types import Message, State, AnalyticsQuestion, AnalyticsCategory


# Import the FastAPI app
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_api_key() -> str:
    """Provide a test API key for authentication."""
    return "test-api-key-12345"


@pytest.fixture
def auth_headers(test_api_key: str) -> Dict[str, str]:
    """Provide authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {test_api_key}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_env_vars(test_api_key: str) -> Generator[None, None, None]:
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {"PP_API_KEY": test_api_key}):
        yield


@pytest.fixture
def client(mock_env_vars) -> TestClient:
    """Provide a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client(mock_env_vars) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_session_store(sample_state):
    """Mock the session store to avoid external dependencies."""
    with patch("app.routers.sessions.session_store") as mock_store_sessions, \
         patch("app.routers.queries.session_store") as mock_store_queries:
        # Configure mock behavior to return proper State objects
        mock_store_sessions.get_state.return_value = sample_state
        mock_store_sessions.delete_session.return_value = None
        mock_store_queries.get_state.return_value = sample_state
        mock_store_queries.delete_session.return_value = None
        
        # Make both mocks return the same thing when modified
        def sync_mocks(new_state):
            mock_store_sessions.get_state.return_value = new_state
            mock_store_queries.get_state.return_value = new_state
        
        mock_store_sessions.sync_state = sync_mocks
        yield mock_store_sessions


@pytest.fixture
def mock_baml_client():
    """Mock the BAML client to avoid external AI API calls."""
    with patch("app.routers.queries.b") as mock_baml:
        yield mock_baml


@pytest.fixture
def sample_analytics_data() -> Dict[str, Any]:
    """Provide sample analytics data for testing."""
    return {
        "category": "USERS",
        "data": {"total_users": 1000, "active_users": 750, "new_registrations": 50},
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_analytics_loader(sample_analytics_data):
    """Mock the analytics data loader."""
    with patch("app.routers.queries.get_analytics_data_for_category") as mock_loader:
        mock_loader.return_value = sample_analytics_data
        yield mock_loader


@pytest.fixture
def sample_message() -> Message:
    """Provide a sample BAML Message for testing."""
    return Message(
        role="assistant",
        content="Hello! I'm here to help with your analytics questions.",
    )


@pytest.fixture
def sample_analytics_question() -> AnalyticsQuestion:
    """Provide a sample BAML AnalyticsQuestion for testing."""
    return AnalyticsQuestion(
        category=AnalyticsCategory.USERS, question="How many users do we have?"
    )


@pytest.fixture
def sample_state() -> State:
    """Provide a sample BAML State for testing."""
    state = State(
        recent_messages=[
            Message(role="assistant", content="Welcome! How can I help you today?")
        ]
    )
    return state


@pytest.fixture
def test_session_id() -> str:
    """Provide a test session ID."""
    return "test-session-12345"


@pytest.fixture
def mock_uuid(test_session_id: str):
    """Mock UUID generation for consistent session IDs."""
    with patch("app.routers.sessions.uuid.uuid4") as mock_uuid4:
        mock_uuid4.return_value = Mock()
        mock_uuid4.return_value.__str__ = Mock(return_value=test_session_id)
        yield mock_uuid4


# Error response fixtures
@pytest.fixture
def unauthorized_response() -> Dict[str, Any]:
    """Expected response for unauthorized requests."""
    return {"detail": "Invalid API key"}


@pytest.fixture
def missing_session_response() -> Dict[str, Any]:
    """Expected response for missing session header."""
    return {"detail": "Missing X-Session-ID header"}


@pytest.fixture
def server_error_response() -> Dict[str, Any]:
    """Expected response for server errors."""
    return {"detail": "PP_API_KEY not configured"}


# Test data generators
@pytest.fixture
def valid_query_payload() -> Dict[str, str]:
    """Provide a valid query payload."""
    return {"message": "How many users do we have?"}


@pytest.fixture
def invalid_query_payload() -> Dict[str, Any]:
    """Provide an invalid query payload."""
    return {"invalid_field": "test"}


@pytest.fixture
def session_headers(
    auth_headers: Dict[str, str], test_session_id: str
) -> Dict[str, str]:
    """Provide headers with session ID for query endpoint."""
    return {**auth_headers, "X-Session-ID": test_session_id}
