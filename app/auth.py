"""
Authentication utilities for the ParentPass Chatbot API.
"""

import os
from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# Security
security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key."""
    expected_api_key = os.getenv("PP_API_KEY")
    if not expected_api_key:
        raise HTTPException(status_code=500, detail="PP_API_KEY not configured")
    if credentials.credentials != expected_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return credentials.credentials


def get_session_from_header(request: Request) -> str:
    """Extract session ID from X-Session-ID header."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-ID header")
    return session_id 