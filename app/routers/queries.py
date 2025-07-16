"""
Query processing router for the ParentPass Chatbot API.
"""

import time
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from ..models.responses import QueryResponse, ErrorResponse
from ..models.requests import QueryRequest
from ..auth import verify_api_key, get_session_from_header
from ..session_store import session_store
from ..analytics_loader import get_analytics_data_for_category
from baml_client import b
from baml_client.types import Message, AnalyticsQuestion

router = APIRouter(
    prefix="/api",
    tags=["queries"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Process Query",
    description="Send a message to the chatbot and receive a response",
    responses={
        200: {
            "description": "Query processed successfully",
            "model": QueryResponse,
        },
        400: {
            "description": "Missing X-Session-ID header or invalid request",
            "model": ErrorResponse,
        },
        403: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error or query processing failure",
            "model": ErrorResponse,
        },
    },
)
async def process_query(
    request: Request,
    query_request: QueryRequest,
    api_key: str = Depends(verify_api_key),
) -> QueryResponse:
    """
    Process a user query and return the chatbot's response.
    
    This endpoint processes natural language queries about ParentPass analytics
    and platform data. The chatbot can answer questions about user engagement,
    content creation, neighborhood statistics, and other platform metrics.
    
    Args:
        request: FastAPI request object (used to extract session ID from headers)
        query_request: The user's query message
        api_key: Valid API key (automatically extracted from Authorization header)
    
    Returns:
        QueryResponse: Contains the chatbot's response and metadata
        
    Raises:
        HTTPException: 400 if X-Session-ID header is missing
        HTTPException: 403 if API key is invalid
        HTTPException: 500 if query processing fails
        
    Headers:
        X-Session-ID: Required session identifier for conversation context
        
    Example:
        ```
        curl -X POST \\
             -H "Authorization: Bearer YOUR_API_KEY" \\
             -H "X-Session-ID: 550e8400-e29b-41d4-a716-446655440000" \\
             -H "Content-Type: application/json" \\
             -d '{"message": "Show me user engagement metrics for this week"}' \\
             https://api.parentpass.com/api/query
        ```
        
        Response:
        ```json
        {
            "response": "Based on the analytics data, user engagement has increased by 15% this week. The most popular sections are Events (35% of time) and Recommendations (28% of time).",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2024-01-15T10:30:00Z",
            "processing_time_ms": 1250
        }
        ```
        
    Supported Query Types:
        - User engagement and activity metrics
        - Content creation statistics
        - Neighborhood and community insights
        - Event and activity data
        - Registration and growth trends
        - General platform analytics
        
    Note:
        The chatbot maintains conversation context within each session.
        Analytics data is automatically loaded based on the query type.
    """
    start_time = time.time()
    
    try:
        session_id = get_session_from_header(request)
        state = session_store.get_state(session_id)

        # Add user message to conversation history
        state.recent_messages.append(
            Message(
                role="user",
                content=query_request.message,
            )
        )

        # Step 1: Process the query with the Chat function
        response = await b.Chat(state)

        # Step 2: Handle different response types
        if isinstance(response, Message):
            # Direct response from the chatbot
            response_message = response
        elif isinstance(response, AnalyticsQuestion):
            # Query requires analytics data
            analytics_data = get_analytics_data_for_category(response.category)

            if analytics_data:
                # Process analytics data and generate response
                response_message = await b.AnswerAnalyticsQuestion(
                    state, analytics_data
                )
            else:
                # Analytics data not available
                response_message = Message(
                    role="assistant",
                    content="I don't have access to the analytics data needed to answer your question right now. "
                    "Please try again later or contact support if this issue persists.",
                )
        else:
            # Unexpected response type
            response_message = Message(
                role="assistant",
                content="I'm having trouble processing your request right now. Please try rephrasing your question or try again later.",
            )

        # Add assistant response to conversation history
        state.recent_messages.append(response_message)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        return QueryResponse(
            response=response_message.content,
            session_id=session_id,
            timestamp=datetime.now(),
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like missing session header)
        raise
    except Exception as e:
        # Handle unexpected errors
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the error for debugging
        print(f"Error processing query: {e}")
        
        # Try to get session_id for response, fallback to "unknown"
        try:
            session_id = get_session_from_header(request)
        except:
            session_id = "unknown"
            
        # Add error message to conversation history if possible
        try:
            if session_id != "unknown":
                state = session_store.get_state(session_id)
                error_message = Message(
                    role="assistant",
                    content="I'm having trouble processing your request right now. Please try again.",
                )
                state.recent_messages.append(error_message)
        except:
            # If we can't update the session, just continue
            pass

        return QueryResponse(
            response="I'm having trouble processing your request right now. Please try again.",
            session_id=session_id,
            timestamp=datetime.now(),
            processing_time_ms=processing_time_ms
        ) 