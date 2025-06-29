#!/usr/bin/env python3
"""
API Test Script for ParentPass Analytics Chatbot

This script tests the analytics API by:
1. Creating a session
2. Asking various analytics questions
3. Logging all results to a file

No BAML dependencies required - just standard HTTP requests.
"""

import requests
import json
import time
from datetime import datetime
import os
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000/api"
API_KEY = os.getenv("PP_API_KEY", "dev-api-key-12345")
LOG_FILE = f"api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Test questions covering different analytics types
TEST_QUESTIONS = [
    # CONTENT type questions
    "How much content has been created recently?",
    "What types of posts are being made?",
    "How many activities were created this week?",
    
    # EVENTS type questions  
    "What events are coming up?",
    "How many events are scheduled?",
    "Are there any upcoming activities?",
    
    # REGISTRATIONS type questions
    "How many new users signed up this month?",
    "What's our user growth looking like?",
    "Show me registration trends",
    
    # NEIGHBORHOODS type questions
    "Which neighborhoods are most active?",
    "How are users distributed geographically?",
    "What's the neighborhood breakdown?",
    
    # ENGAGEMENT type questions
    "How engaged are our users?",
    "What's the average time spent in the app?",
    "How are push notifications performing?",
    "What are users searching for?",
    
    # USERS type questions
    "How many daily active users do we have?",
    "Show me our user activity metrics",
    "Who are our most engaged users?",
    
    # General questions
    "Give me an overview of the platform",
    "What should I know about ParentPass performance?",
]

class APITester:
    def __init__(self, base_url: str, api_key: str, log_file: str):
        self.base_url = base_url
        self.api_key = api_key
        self.log_file = log_file
        self.session_id = None
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    def log(self, message: str, also_print: bool = True):
        """Log message to file and optionally print to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            
        if also_print:
            print(log_entry)
    
    def test_health(self) -> bool:
        """Test the health endpoint."""
        self.log("Testing health endpoint...")
        try:
            response = requests.get(f"{self.base_url}/health", headers=self.headers)
            if response.status_code == 200:
                self.log(f"✅ Health check passed: {response.json()}")
                return True
            else:
                self.log(f"❌ Health check failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Health check error: {str(e)}")
            return False
    
    def create_session(self) -> bool:
        """Create a new session."""
        self.log("Creating new session...")
        try:
            response = requests.post(f"{self.base_url}/sessions", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                self.log(f"✅ Session created: {self.session_id}")
                return True
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}")
            return False
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Ask a question to the chatbot."""
        if not self.session_id:
            return {"error": "No active session"}
        
        self.log(f"Asking: {question}")
        
        headers_with_session = {
            **self.headers,
            "X-Session-ID": self.session_id
        }
        
        payload = {"message": question}
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/query", 
                headers=headers_with_session,
                json=payload
            )
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Response ({response_time:.2f}s): {data['response']}")
                return {
                    "success": True,
                    "question": question,
                    "response": data["response"],
                    "response_time": response_time
                }
            else:
                error_msg = f"Query failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}")
                return {
                    "success": False,
                    "question": question,
                    "error": error_msg,
                    "response_time": response_time
                }
                
        except Exception as e:
            error_msg = f"Query error: {str(e)}"
            self.log(f"❌ {error_msg}")
            return {
                "success": False,
                "question": question,
                "error": error_msg
            }
    
    def get_session_state(self) -> Dict[str, Any]:
        """Get current session state."""
        if not self.session_id:
            return {"error": "No active session"}
            
        try:
            response = requests.get(
                f"{self.base_url}/sessions/{self.session_id}", 
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get session: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def run_full_test(self):
        """Run the complete test suite."""
        self.log("=" * 60)
        self.log("Starting ParentPass Analytics API Test")
        self.log("=" * 60)
        
        # Test health
        if not self.test_health():
            self.log("❌ Health check failed, aborting tests")
            return
        
        # Create session
        if not self.create_session():
            self.log("❌ Session creation failed, aborting tests")
            return
        
        # Test questions
        results = []
        self.log(f"\nTesting {len(TEST_QUESTIONS)} questions...")
        self.log("-" * 40)
        
        for i, question in enumerate(TEST_QUESTIONS, 1):
            self.log(f"\n[Question {i}/{len(TEST_QUESTIONS)}]")
            result = self.ask_question(question)
            results.append(result)
            
            # Brief pause between questions
            time.sleep(1)
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("Test Summary")
        self.log("=" * 60)
        
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        avg_response_time = sum(r.get("response_time", 0) for r in results if "response_time" in r) / len(results)
        
        self.log(f"Total questions: {len(results)}")
        self.log(f"Successful: {successful}")
        self.log(f"Failed: {failed}")
        self.log(f"Success rate: {successful/len(results)*100:.1f}%")
        self.log(f"Average response time: {avg_response_time:.2f}s")
        
        # Get final session state
        self.log("\nFinal session state:")
        session_state = self.get_session_state()
        if "error" not in session_state:
            message_count = len(session_state.get("state", {}).get("recent_messages", []))
            self.log(f"Total messages in conversation: {message_count}")
        
        self.log(f"\nTest completed. Results logged to: {self.log_file}")

def main():
    """Main function to run the API test."""
    print("ParentPass Analytics API Tester")
    print("=" * 40)
    
    # Check if server is likely running
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        print("✅ Server appears to be running")
    except:
        print("⚠️  Warning: Server may not be running at localhost:8000")
        print("   Make sure to start the server first!")
        choice = input("Continue anyway? (y/N): ")
        if choice.lower() != 'y':
            return
    
    # Initialize tester
    tester = APITester(API_BASE_URL, API_KEY, LOG_FILE)
    
    print(f"Logging results to: {LOG_FILE}")
    print("Starting tests...\n")
    
    # Run tests
    tester.run_full_test()

if __name__ == "__main__":
    main() 