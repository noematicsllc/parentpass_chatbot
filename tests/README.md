# ParentPass Chatbot API Test Suite

A comprehensive test suite for the ParentPass Chatbot API covering all endpoints with unit tests, integration tests, authentication tests, error handling, and performance validation.

## Test Structure

```
tests/
├── __init__.py                    # Test package
├── conftest.py                   # Pytest fixtures and configuration
├── test_health_endpoint.py       # Health endpoint tests
├── test_session_endpoints.py     # Session management tests
├── test_query_endpoint.py        # Query/chatbot functionality tests
├── test_authentication.py        # API key authentication tests
├── test_error_handling.py        # Error scenarios and edge cases
├── test_integration.py           # End-to-end workflow tests
├── run_tests.py                  # Test runner script
└── README.md                     # This file
```

## Quick Start

### Prerequisites

```bash
uv sync --dev
```

### Running Tests

#### Using the Test Runner Script (Recommended)

```bash
# Run all tests with coverage
uv run python tests/run_tests.py

# Run specific test categories
uv run python tests/run_tests.py health      # Health endpoint only
uv run python tests/run_tests.py sessions    # Session management only
uv run python tests/run_tests.py query       # Query endpoint only
uv run python tests/run_tests.py auth        # Authentication tests only
uv run python tests/run_tests.py errors      # Error handling tests only
uv run python tests/run_tests.py integration # Integration tests only

# With options
uv run python tests/run_tests.py --verbose             # Verbose output
uv run python tests/run_tests.py --quick               # Fast run, no coverage
uv run python tests/run_tests.py --no-coverage         # Skip coverage
```

#### Using pytest Directly

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run specific test files
uv run pytest tests/test_health_endpoint.py
```

## Test Categories

### Health Endpoint Tests
Tests the `/api/health` endpoint for successful checks, authentication failures, and performance validation.

### Session Management Tests
Tests session endpoints for creation, retrieval, deletion, lifecycle management, and concurrent handling.

### Query Endpoint Tests
Tests the main chatbot functionality including BAML client integration, analytics questions, and session state management.

### Authentication Tests
Tests API key authentication across all endpoints with valid/invalid scenarios and security edge cases.

### Error Handling Tests
Tests error scenarios including BAML client failures, network errors, and concurrent request handling.

### Integration Tests
Tests complete end-to-end workflows including full conversations, analytics categories, and session persistence.

## Test Configuration

Key fixtures available in `conftest.py`:
- `client`: FastAPI test client
- `auth_headers`: Valid authentication headers
- `mock_session_store`: Mocked session store
- `mock_baml_client`: Mocked BAML AI client
- `sample_analytics_data`: Test analytics data

The test suite mocks external dependencies including the session store, BAML client, and analytics loader.

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure

```python
class TestNewFeature:
    """Test cases for new feature."""

    def test_success_scenario(self, client, auth_headers):
        """Test successful operation."""
        response = client.get("/api/new-endpoint", headers=auth_headers)
        assert response.status_code == 200
```

## Coverage Reporting

View coverage reports at `htmlcov/index.html` after running tests with coverage. 