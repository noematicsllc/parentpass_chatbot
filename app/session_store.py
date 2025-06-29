from typing import Dict
from datetime import datetime, timedelta
from baml_client.types import State, Message
from .session_state import create_state

class SessionData:
    """Simple wrapper to track session creation time."""
    def __init__(self, state: State):
        self.state = state
        self.created_at = datetime.now()

class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
    
    def get_state(self, session_id: str) -> State:
        """Get the state for a session, creating a new one if it doesn't exist."""
        # Clean up expired sessions when accessing
        self._cleanup_expired_sessions()
        
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionData(initial_state())
        return self._sessions[session_id].state
    
    def set_state(self, session_id: str, state: State) -> None:
        """Update the state for a session."""
        if session_id in self._sessions:
            self._sessions[session_id].state = state
        else:
            self._sessions[session_id] = SessionData(state)
    
    def delete_session(self, session_id: str) -> None:
        """Remove a session and its state."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def _cleanup_expired_sessions(self):
        """Remove sessions older than 4 hours."""
        cutoff = datetime.now() - timedelta(hours=4)
        expired = [sid for sid, session_data in self._sessions.items() 
                  if session_data.created_at < cutoff]
        for sid in expired:
            del self._sessions[sid]

# Create a global session store instance
session_store = SessionStore() 

def initial_state() -> State:
    """Create initial state with a welcome message for administrators."""
    state = create_state()
    
    # Add welcome message
    welcome_message = Message(
        role="assistant",
        content="Hello! I'm the ParentPass administrative assistant. How can I help you analyze the platform today?"
    )
    state.recent_messages.append(welcome_message)
    
    return state
