"""
Response models for ParentPass Chatbot API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(
        ...,
        description="Health status of the API"
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when health check was performed"
    )
    version: Optional[str] = Field(
        default=None,
        description="API version"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0"
            }
        }


class QueryResponse(BaseModel):
    """Response model for chatbot query endpoint."""
    
    response: str = Field(
        ...,
        description="The chatbot's response to the user's query"
    )
    session_id: str = Field(
        ...,
        description="Session ID associated with this query"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the response was generated"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Time taken to process the query in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on the analytics data, user engagement has increased by 15% this month. The most popular sections are Events and Recommendations.",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-01-15T10:30:00Z",
                "processing_time_ms": 1250
            }
        }


class DeleteSessionResponse(BaseModel):
    """Response model for session deletion endpoint."""
    
    deleted: bool = Field(
        ...,
        description="Whether the session was successfully deleted"
    )
    session_id: str = Field(
        ...,
        description="ID of the deleted session"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the session was deleted"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "deleted": True,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    
    error: str = Field(
        ...,
        description="Error message"
    )
    detail: Optional[str] = Field(
        default=None,
        description="Detailed error information"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the error occurred"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid API key",
                "detail": "The provided API key is not valid or has expired",
                "timestamp": "2024-01-15T10:30:00Z",
                "error_code": "AUTH_001"
            }
        } 