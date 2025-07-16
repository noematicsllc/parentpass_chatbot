from fastapi import FastAPI
import logging
from dotenv import load_dotenv

# Import routers
from .routers import health, sessions, queries

load_dotenv()
logging.basicConfig(level=logging.WARNING)

app = FastAPI(
    title="ParentPass Chatbot API",
    description="Administrative chatbot API for ParentPass analytics and platform data",
    version="1.0.0",
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "sessions",
            "description": "Session management for chatbot conversations",
        },
        {
            "name": "queries",
            "description": "Process natural language queries about ParentPass data",
        },
    ],
)

# Include routers
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(queries.router)
