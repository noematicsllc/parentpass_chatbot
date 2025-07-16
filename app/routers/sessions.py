"""
Session management router for the ParentPass Chatbot API.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from ..models.responses import DeleteSessionResponse, ErrorResponse
from ..models.requests import SessionResponse
from ..auth import verify_api_key
from ..session_store import session_store

router = APIRouter(
    prefix="/api",
    tags=["sessions"],
    responses={
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.post(
    "/sessions",
    response_model=SessionResponse,
    summary="Create Session",
    description="Create a new chatbot session",
    responses={
        201: {
            "description": "Session created successfully",
            "model": SessionResponse,
        },
        403: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
    status_code=201,
)
def create_session(api_key: str = Depends(verify_api_key)) -> SessionResponse:
    """
    Create a new chatbot session.
    
    This endpoint creates a new session for interacting with the chatbot.
    Each session maintains its own conversation history and state.
    Sessions automatically expire after 4 hours of inactivity.
    
    Args:
        api_key: Valid API key (automatically extracted from Authorization header)
    
    Returns:
        SessionResponse: Contains the new session ID and initial state
        
    Raises:
        HTTPException: 403 if API key is invalid
        HTTPException: 500 if PP_API_KEY environment variable is not configured
        
    Example:
        ```
        curl -X POST \\
             -H "Authorization: Bearer YOUR_API_KEY" \\
             https://api.parentpass.com/api/sessions
        ```
        
        Response:
        ```json
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "state": {
                "recent_messages": [
                    {
                        "role": "assistant",
                        "content": "Hello! I'm the ParentPass administrative assistant..."
                    }
                ]
            }
        }
        ```
    """
    session_id = str(uuid.uuid4())
    state = session_store.get_state(session_id)
    return SessionResponse(session_id=session_id, state=state)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get Session",
    description="Retrieve the current state of a chatbot session",
    responses={
        200: {
            "description": "Session retrieved successfully",
            "model": SessionResponse,
        },
        403: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse,
        },
        404: {
            "description": "Session not found or expired",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
def get_session(
    session_id: str, api_key: str = Depends(verify_api_key)
) -> SessionResponse:
    """
    Retrieve the current state of a chatbot session.
    
    This endpoint returns the current state of an existing session,
    including the conversation history and any stored context.
    
    Args:
        session_id: The unique identifier of the session to retrieve
        api_key: Valid API key (automatically extracted from Authorization header)
    
    Returns:
        SessionResponse: Contains the session ID and current state
        
    Raises:
        HTTPException: 403 if API key is invalid
        HTTPException: 404 if session is not found or has expired
        HTTPException: 500 if PP_API_KEY environment variable is not configured
        
    Example:
        ```
        curl -H "Authorization: Bearer YOUR_API_KEY" \\
             https://api.parentpass.com/api/sessions/550e8400-e29b-41d4-a716-446655440000
        ```
        
        Response:
        ```json
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "state": {
                "recent_messages": [
                    {
                        "role": "assistant",
                        "content": "Hello! I'm the ParentPass administrative assistant..."
                    },
                    {
                        "role": "user",
                        "content": "Show me user engagement metrics"
                    }
                ]
            }
        }
        ```
    """
    try:
        state = session_store.get_state(session_id)
        return SessionResponse(session_id=session_id, state=state)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found or has expired"
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete Session",
    description="Delete a chatbot session and clear its state",
    responses={
        200: {
            "description": "Session deleted successfully",
            "model": DeleteSessionResponse,
        },
        403: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
def delete_session(
    session_id: str, api_key: str = Depends(verify_api_key)
) -> DeleteSessionResponse:
    """
    Delete a chatbot session and clear its state.
    
    This endpoint permanently removes a session and all associated data.
    Once deleted, the session cannot be recovered and a new session
    must be created for future interactions.
    
    Args:
        session_id: The unique identifier of the session to delete
        api_key: Valid API key (automatically extracted from Authorization header)
    
    Returns:
        DeleteSessionResponse: Confirmation of deletion with timestamp
        
    Raises:
        HTTPException: 403 if API key is invalid
        HTTPException: 500 if PP_API_KEY environment variable is not configured
        
    Note:
        This endpoint will return success even if the session doesn't exist.
        This is intentional to ensure idempotent behavior.
        
    Example:
        ```
        curl -X DELETE \\
             -H "Authorization: Bearer YOUR_API_KEY" \\
             https://api.parentpass.com/api/sessions/550e8400-e29b-41d4-a716-446655440000
        ```
        
        Response:
        ```json
        {
            "deleted": true,
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        ```
    """
    session_store.delete_session(session_id)
    return DeleteSessionResponse(
        deleted=True,
        session_id=session_id,
        timestamp=datetime.now()
    ) 