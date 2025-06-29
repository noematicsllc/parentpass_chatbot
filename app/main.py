from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import uuid
import logging
from dotenv import load_dotenv

load_dotenv()

from .session_store import session_store
from .analytics_loader import get_analytics_data_for_category
from baml_client import b
from baml_client.types import Message, State, AnalyticsQuestion

logging.basicConfig(level=logging.WARNING)
app = FastAPI(title="ParentPass Chatbot API")
class QueryRequest(BaseModel):
    message: str

class SessionResponse(BaseModel):
    session_id: str
    state: State


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


@app.get("/api/health")
def health_check(api_key: str = Depends(verify_api_key)):
    return {"status": "ok"}

# API endpoints (session-based with API key authentication)
@app.post("/api/sessions")
def create_session(api_key: str = Depends(verify_api_key)) -> SessionResponse:
    """Create a new session."""
    session_id = str(uuid.uuid4())
    state = session_store.get_state(session_id)
    return SessionResponse(session_id=session_id, state=state)

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, api_key: str = Depends(verify_api_key)) -> SessionResponse:
    """Get session state."""
    state = session_store.get_state(session_id)
    return SessionResponse(session_id=session_id, state=state)

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a session."""
    session_store.delete_session(session_id)
    return {"deleted": True}

@app.post("/api/query")
async def query(request: Request, query_request: QueryRequest, api_key: str = Depends(verify_api_key)):
    """Send a message to the chatbot."""
    session_id = get_session_from_header(request)
    state = session_store.get_state(session_id)
    
    state.recent_messages.append(Message(
        role="user", 
        content=query_request.message, 
    ))
    
    try:
        # Step 1: Start with the Chat function
        response = await b.Chat(state)
        
        # Step 2: Check if we got a Message or AnalyticsQuestion
        if isinstance(response, Message):
            # We got a direct response, use it
            response_message = response
        elif isinstance(response, AnalyticsQuestion):
            analytics_data = get_analytics_data_for_category(response.category)
            
            if analytics_data:
                response_message = await b.AnswerAnalyticsQuestion(state, analytics_data)
            else:
                response_message = Message(
                    role="assistant", 
                    content="I don't have access to the analytics data needed to answer your question right now. Please try again later."
                )
        else:
            response_message = Message(
                role="assistant", 
                content="I'm having trouble processing your request right now. Please try again."
            )
        
        state.recent_messages.append(response_message)
        
        return {"response": response_message.content}
        
    except Exception as e:
        print(f"Error processing query: {e}")
        response_message = Message(
            role="assistant", 
            content="I'm having trouble processing your request right now. Please try again."
        )
        
        state.recent_messages.append(response_message)
        return {"response": response_message.content}

