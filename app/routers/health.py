"""
Health check router for the ParentPass Chatbot API.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from ..models.responses import HealthResponse, ErrorResponse
from ..auth import verify_api_key

router = APIRouter(
    prefix="/api",
    tags=["health"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the ParentPass Chatbot API",
    responses={
        200: {
            "description": "API is healthy and operational",
            "model": HealthResponse,
        },

        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
def health_check() -> HealthResponse:
    """
    Perform a health check on the API.
    
    This endpoint verifies that the API is running and accessible.
    No authentication required for monitoring purposes.
    
    Returns:
        HealthResponse: Contains status information and timestamp
        
    Raises:
        HTTPException: 500 if there are internal server issues
        
    Example:
        ```
        curl https://api.parentpass.com/api/health
        ```
        
        Response:
        ```json
        {
            "status": "ok",
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "1.0.0"
        }
        ```
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(),
        version="1.0.0"
    ) 