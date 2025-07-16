#!/usr/bin/env python3
"""
Simple CLI chatbot for ParentPass API
"""
import requests
import os
import sys
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
# Configuration
API_BASE_URL = "http://localhost:8000/api"
API_KEY = os.getenv("PP_API_KEY")
if not API_KEY:
    print("Error: Please set PP_API_KEY environment variable")
    sys.exit(1)
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def create_session():
    """Create a new chat session and return session_id and welcome message"""
    response = requests.post(f"{API_BASE_URL}/sessions", headers=headers)
    if response.status_code == 200:
        data = response.json()
        session_id = data["session_id"]

        # Extract welcome message from the initial state
        _welcome_message = None
        if "state" in data and "recent_messages" in data["state"]:
            messages = data["state"]["recent_messages"]
            if messages and messages[0]["role"] == "assistant":
                _welcome_message = messages[0]["content"]

        return session_id, _welcome_message
    else:
        print(f"Failed to create session: {response.status_code}")
        sys.exit(1)


def format_response(text):
    """Format response text by converting ==emphasis== to bold text"""

    # Replace ==text== with bold ANSI codes
    formatted = re.sub(r"==(.*?)==", r"\033[1m\1\033[0m", text)
    return formatted


def ask_question(session_id, message):
    """Send a message to the chatbot"""
    session_headers = {**headers, "X-Session-ID": session_id}
    payload = {"message": message}

    response = requests.post(
        f"{API_BASE_URL}/query", headers=session_headers, json=payload
    )
    if response.status_code == 200:
        return format_response(response.json()["response"])
    else:
        return f"Error: {response.status_code} - {response.text}"


def delete_session(session_id):
    """Clean up the session"""
    requests.delete(f"{API_BASE_URL}/sessions/{session_id}", headers=headers)


def main():
    print("ParentPass Chatbot CLI")
    print("Type 'quit' or 'exit' to end the conversation")
    print("-" * 50)

    # Create session
    session_id, _welcome_message = create_session()
    print(f"Session created: {session_id}")

    # Show welcome message if available
    if _welcome_message:
        print(f"Bot: {format_response(_welcome_message)}")

    try:
        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                break

            if not user_input:
                continue

            response = ask_question(session_id, user_input)
            print(f"Bot: {response}")

    except KeyboardInterrupt:
        print("\nGoodbye!")

    finally:
        # Clean up session
        delete_session(session_id)
        print(f"Session {session_id} closed.")


if __name__ == "__main__":
    main()
