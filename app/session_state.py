# Load environment variables from .env file

from baml_client.types import State
from dotenv import load_dotenv

load_dotenv()


def create_state() -> State:
    """Create a new state for administrators."""
    return State(recent_messages=[])


def sample_state() -> State:
    """Backward compatibility function."""
    return create_state()
