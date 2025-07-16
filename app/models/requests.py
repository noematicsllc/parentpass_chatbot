"""
Request models for ParentPass Chatbot API endpoints.
"""

from pydantic import BaseModel, Field
from baml_client.types import State


class QueryRequest(BaseModel):
    """Request model for chatbot query endpoint."""
    
    message: str = Field(
        ...,
        description="The user's message to send to the chatbot"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me user engagement metrics for this week"
            }
        }


class SessionResponse(BaseModel):
    """Response model for session-related endpoints."""
    
    session_id: str = Field(
        ...,
        description="Unique identifier for the session"
    )
    state: State = Field(
        ...,
        description="Current state of the session including conversation history"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
        } 