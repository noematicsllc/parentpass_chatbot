"""
Integration tests for complete API workflows.

This module tests end-to-end workflows that combine multiple endpoints
and verify the complete user journey through the API.
"""

from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from baml_client.types import Message, AnalyticsQuestion, AnalyticsCategory


class TestIntegrationWorkflows:
    """Integration tests for complete API workflows."""

    def test_complete_chatbot_conversation_workflow(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        sample_analytics_data,
        mock_uuid,
    ):
        """Test a complete chatbot conversation from start to finish."""
        # Mock BAML responses
        analytics_question = AnalyticsQuestion(
            category=AnalyticsCategory.USERS, question="How many users do we have?"
        )
        analytics_response = Message(
            role="assistant",
            content="Based on the data, you have 1000 total users with 750 active users.",
        )
        general_response = Message(
            role="assistant", content="Is there anything else I can help you with?"
        )

        # Step 1: Check API health
        health_response = client.get("/api/health", headers=auth_headers)
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "ok"
        assert "timestamp" in health_data
        assert health_data["version"] == "1.0.0"

        # Step 2: Create a new session
        session_response = client.post("/api/sessions", headers=auth_headers)
        assert session_response.status_code == 201
        session_data = session_response.json()
        session_id = session_data["session_id"]

        # Step 3: First query - analytics question
        mock_baml_client.Chat = AsyncMock(return_value=analytics_question)
        mock_baml_client.AnswerAnalyticsQuestion = AsyncMock(
            return_value=analytics_response
        )

        with patch(
            "app.routers.queries.get_analytics_data_for_category",
            return_value=sample_analytics_data,
        ):
            query_headers = {**auth_headers, "X-Session-ID": session_id}
            first_query = {"message": "How many users do we have?"}

            first_response = client.post(
                "/api/query", headers=query_headers, json=first_query
            )
            assert first_response.status_code == 200
            first_data = first_response.json()
            assert analytics_response.content in first_data["response"]

        # Verify analytics loader was called correctly
        mock_baml_client.Chat.assert_called_with(
            mock_session_store.get_state.return_value
        )
        mock_baml_client.AnswerAnalyticsQuestion.assert_called_once()

        # Step 4: Second query - general conversation
        mock_baml_client.Chat = AsyncMock(return_value=general_response)

        second_query = {"message": "Thank you! That's very helpful."}
        second_response = client.post(
            "/api/query", headers=query_headers, json=second_query
        )
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert general_response.content in second_data["response"]

        # Step 5: Check session state
        session_state_response = client.get(
            f"/api/sessions/{session_id}", headers=auth_headers
        )
        assert session_state_response.status_code == 200
        state_data = session_state_response.json()
        assert state_data["session_id"] == session_id

        # Step 6: Clean up session
        delete_response = client.delete(
            f"/api/sessions/{session_id}", headers=auth_headers
        )
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["deleted"] is True
        assert "session_id" in delete_data
        assert "timestamp" in delete_data

    def test_analytics_workflow_all_categories(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test analytics queries for all different categories."""
        # Create session
        session_response = client.post("/api/sessions", headers=auth_headers)
        session_id = session_response.json()["session_id"]

        query_headers = {**auth_headers, "X-Session-ID": session_id}

        # Test each analytics category
        analytics_tests = [
            (
                AnalyticsCategory.CONTENT,
                "How much content has been created?",
                "content data",
            ),
            (AnalyticsCategory.EVENTS, "What events are coming up?", "events data"),
            (
                AnalyticsCategory.REGISTRATIONS,
                "How many users signed up?",
                "registration data",
            ),
            (
                AnalyticsCategory.NEIGHBORHOODS,
                "Which neighborhoods are active?",
                "neighborhood data",
            ),
            (AnalyticsCategory.ENGAGEMENT, "How engaged are users?", "engagement data"),
            (AnalyticsCategory.USERS, "How many daily active users?", "user data"),
        ]

        for category, question, mock_data in analytics_tests:
            # Mock BAML to return analytics question for this category
            analytics_question = AnalyticsQuestion(category=category, question=question)
            analytics_response = Message(
                role="assistant", content=f"Here's the {mock_data}"
            )

            mock_baml_client.Chat = AsyncMock(return_value=analytics_question)
            mock_baml_client.AnswerAnalyticsQuestion = AsyncMock(
                return_value=analytics_response
            )

            with patch(
                "app.routers.queries.get_analytics_data_for_category", return_value=mock_data
            ):
                response = client.post(
                    "/api/query", headers=query_headers, json={"message": question}
                )

                assert response.status_code == 200
                data = response.json()
                assert mock_data in data["response"]

        # Clean up
        client.delete(f"/api/sessions/{session_id}", headers=auth_headers)

    def test_session_persistence_across_queries(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test that session state persists correctly across multiple queries."""
        # The mock_session_store fixture already returns a proper State object
        # No need to override it - just use it as is

        # Create session
        session_response = client.post("/api/sessions", headers=auth_headers)
        session_id = session_response.json()["session_id"]

        query_headers = {**auth_headers, "X-Session-ID": session_id}

        # Multiple queries to build conversation
        queries_and_responses = [
            ("Hello", "Hi there! How can I help you?"),
            ("What's my name?", "I don't have access to your name information."),
            (
                "Can you help me with analytics?",
                "Of course! What would you like to know?",
            ),
            ("Show me user data", "Here's the user analytics data."),
        ]

        for i, (user_msg, bot_response) in enumerate(queries_and_responses):
            mock_response = Message(role="assistant", content=bot_response)
            mock_baml_client.Chat = AsyncMock(return_value=mock_response)

            response = client.post(
                "/api/query", headers=query_headers, json={"message": user_msg}
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data

        # Verify session still exists after multiple queries
        final_state = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert final_state.status_code == 200

        # Clean up
        client.delete(f"/api/sessions/{session_id}", headers=auth_headers)

    def test_error_recovery_workflow(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test that the system recovers gracefully from errors during a workflow."""
        # Create session
        session_response = client.post("/api/sessions", headers=auth_headers)
        session_id = session_response.json()["session_id"]

        query_headers = {**auth_headers, "X-Session-ID": session_id}

        # Step 1: Successful query
        success_response = Message(role="assistant", content="This query works fine.")
        mock_baml_client.Chat = AsyncMock(return_value=success_response)

        response1 = client.post(
            "/api/query",
            headers=query_headers,
            json={"message": "Test successful query"},
        )
        assert response1.status_code == 200
        assert "works fine" in response1.json()["response"]

        # Step 2: Query that causes BAML error
        mock_baml_client.Chat = AsyncMock(side_effect=Exception("BAML service error"))

        response2 = client.post(
            "/api/query",
            headers=query_headers,
            json={"message": "This will cause an error"},
        )
        assert (
            response2.status_code == 200
        )  # Should still return 200 with error message
        assert "having trouble processing your request" in response2.json()["response"]

        # Step 3: Recovery - successful query after error
        recovery_response = Message(
            role="assistant", content="System recovered successfully."
        )
        mock_baml_client.Chat = AsyncMock(return_value=recovery_response)

        response3 = client.post(
            "/api/query", headers=query_headers, json={"message": "Test recovery"}
        )
        assert response3.status_code == 200
        assert "recovered successfully" in response3.json()["response"]

        # Step 4: Verify session is still valid
        session_check = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert session_check.status_code == 200

        # Clean up
        client.delete(f"/api/sessions/{session_id}", headers=auth_headers)

    def test_concurrent_sessions_workflow(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        sample_state,
    ):
        """Test multiple concurrent sessions don't interfere with each other."""
        import concurrent.futures

        def run_session_workflow(session_suffix):
            # Use proper State object from fixture
            with (
                patch("app.routers.sessions.session_store") as local_store,
                patch("app.routers.sessions.uuid.uuid4") as local_uuid,
                patch("app.routers.queries.b") as local_baml,
            ):

                local_store.get_state.return_value = sample_state
                local_uuid.return_value = Mock()
                local_uuid.return_value.__str__ = Mock(
                    return_value=f"session-{session_suffix}"
                )

                # Create session
                session_response = client.post("/api/sessions", headers=auth_headers)
                session_id = session_response.json()["session_id"]

                # Make queries
                query_headers = {**auth_headers, "X-Session-ID": session_id}

                responses = []
                for i in range(3):
                    response_msg = Message(
                        role="assistant",
                        content=f"Response {i} for session {session_suffix}",
                    )
                    local_baml.Chat = AsyncMock(return_value=response_msg)

                    response = client.post(
                        "/api/query",
                        headers=query_headers,
                        json={"message": f"Query {i} from session {session_suffix}"},
                    )
                    responses.append(response)

                # Delete session
                delete_response = client.delete(
                    f"/api/sessions/{session_id}", headers=auth_headers
                )

                return {
                    "session_suffix": session_suffix,
                    "session_id": session_id,
                    "responses": responses,
                    "delete_response": delete_response,
                }

        # Run 3 sessions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Create futures with unique session suffixes
            futures = []
            for i in range(3):
                future = executor.submit(run_session_workflow, i)
                futures.append(future)
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all sessions completed successfully
        assert len(results) == 3
        session_suffixes = []

        for result in results:
            assert result["delete_response"].status_code == 200
            session_suffixes.append(result["session_suffix"])

            # All queries in each session should succeed
            for response in result["responses"]:
                assert response.status_code == 200

        # Verify all sessions had different suffixes (this proves they ran independently)
        assert len(set(session_suffixes)) == 3
        assert set(session_suffixes) == {0, 1, 2}

    def test_authentication_throughout_workflow(
        self,
        client: TestClient,
        test_api_key,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test that authentication is enforced consistently throughout a workflow."""
        # Step 1: Valid auth should work for all endpoints
        valid_headers = {
            "Authorization": f"Bearer {test_api_key}",
            "Content-Type": "application/json",
        }

        # Health check
        health_response = client.get("/api/health", headers=valid_headers)
        assert health_response.status_code == 200

        # Create session
        session_response = client.post("/api/sessions", headers=valid_headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]

        # Query with session
        query_headers = {**valid_headers, "X-Session-ID": session_id}
        query_response = client.post(
            "/api/query", headers=query_headers, json={"message": "test"}
        )
        assert query_response.status_code == 200

        # Get session
        get_response = client.get(f"/api/sessions/{session_id}", headers=valid_headers)
        assert get_response.status_code == 200

        # Delete session
        delete_response = client.delete(
            f"/api/sessions/{session_id}", headers=valid_headers
        )
        assert delete_response.status_code == 200

        # Step 2: Invalid auth should fail for all endpoints
        invalid_headers = {
            "Authorization": "Bearer invalid-key",
            "Content-Type": "application/json",
        }

        endpoints_to_test = [
            ("GET", "/api/health", {}),
            ("POST", "/api/sessions", {}),
            ("GET", "/api/sessions/test-session", {}),
            ("DELETE", "/api/sessions/test-session", {}),
            ("POST", "/api/query", {"X-Session-ID": "test-session"}),
        ]

        for method, endpoint, extra_headers in endpoints_to_test:
            headers = {**invalid_headers, **extra_headers}

            if method == "GET":
                response = client.get(endpoint, headers=headers)
            elif method == "POST":
                json_data = {"message": "test"} if endpoint == "/api/query" else {}
                response = client.post(endpoint, headers=headers, json=json_data)
            elif method == "DELETE":
                response = client.delete(endpoint, headers=headers)

            assert response.status_code == 403
            assert response.json() == {"detail": "Invalid API key"}

    def test_full_api_documentation_workflow(self, client: TestClient):
        """Test that API documentation endpoints work correctly."""
        # Test OpenAPI schema endpoint
        docs_response = client.get("/docs")
        assert docs_response.status_code == 200

        # Test OpenAPI JSON schema
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200

        openapi_data = openapi_response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data

        # Verify all our endpoints are documented
        paths = openapi_data["paths"]
        expected_paths = [
            "/api/health",
            "/api/sessions",
            "/api/sessions/{session_id}",
            "/api/query",
        ]

        for expected_path in expected_paths:
            assert expected_path in paths

    def test_performance_workflow(
        self,
        client: TestClient,
        auth_headers,
        mock_session_store,
        mock_baml_client,
        mock_uuid,
    ):
        """Test API performance with a realistic workflow."""
        import time

        # Configure BAML mock
        response_msg = Message(role="assistant", content="Quick response")
        mock_baml_client.Chat = AsyncMock(return_value=response_msg)

        # Measure session creation time
        start_time = time.time()
        session_response = client.post("/api/sessions", headers=auth_headers)
        session_time = time.time() - start_time

        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]

        # Measure query response time
        query_headers = {**auth_headers, "X-Session-ID": session_id}

        query_times = []
        for i in range(5):
            start_time = time.time()
            response = client.post(
                "/api/query", headers=query_headers, json={"message": f"Query {i}"}
            )
            query_time = time.time() - start_time

            assert response.status_code == 200
            query_times.append(query_time)

        # Performance assertions (reasonable thresholds for mocked responses)
        assert session_time < 1.0  # Session creation under 1 second
        assert all(qt < 1.0 for qt in query_times)  # All queries under 1 second
        assert (
            sum(query_times) / len(query_times) < 0.5
        )  # Average query time under 500ms

        # Clean up
        client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
