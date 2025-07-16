# ParentPass Chatbot API

A FastAPI-based chatbot API for ParentPass that provides intelligent responses and analytics data access using BAML (Boundary ML) for LLM orchestration.

## Changelog 2025-07-16

Implemented recommendations:
- Refactored endpoints into separate routers for health, queries, and sessions.
- Added response models, improved docstrings
- Added support for Docker deployment
- Used `flake8` and `black` for linting

Notes:
- Response code for session creation endpoint (`POST /api/sessions`) now returns HTTP status **201 (Created)** instead of **200 (OK)** to follow REST API best practices
- Docker configuration will have to be modified according to gcloud authentication practices.
- All endpoint URLs remain unchanged
- Request formats remain unchanged, response formats are backwards compatible.
- BAML updated to version 0.202.00
- Added basic pytest framework
- Added a basic cli client for convenient interactive testing

## Quick Start (Docker)

### Prerequisites
- Docker and Docker Compose installed
- Google Cloud CLI installed (`gcloud`)
- Access to a Google Cloud project with BigQuery

### Setup
1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

**Note:** This method will use your local gcloud credentials (Application Default Credentials) mounted from `/your/home/path/.config/gcloud`. If you use another authentication method (ie, service account), edit `.env` and the `docker-compose.yml` file for your environment.

2. **Configure environment:**
   ```bash
   cp env.docker.example .env
   # Edit .env with your actual values
   ```

3. **Build and run:**
   ```bash
   docker-compose build
   docker-compose up
   ```



## Quick Start (Local Development)

### Prerequisites

- Python 3.10+ (required for match/case syntax)
- [UV package manager](https://docs.astral.sh/uv/)
- Azure SQL Credentials (configured in `.env`)
- Google Cloud/BigQuery credentials (authenticate using gcloud CLI)

### Installation

   ```bash
   # clone this repository and cd into the root folder
   uv sync
   source .venv/bin/activate
   uv run baml-cli generate
   ```

## Configuration

Rename `.env.example` to `.env` and edit with project details and credentials.

## Analytics Generation

The project includes automated analytics report generation that intended to be scheduled via cron jobs.

IMPORTANT: Azure credentials must be present in `.env` and you must be authenticated via gcloud CLI with an account with all necessary permissions.

### Automated Nightly Generation via Cron

Set up a cron job to generate analytics reports automatically:

```bash
# Edit crontab
crontab -e

# Add this line to run analytics generation daily at 2 AM
0 2 * * * cd /path/to/parentpass_chatbot_api && /path/to/.venv/bin/python generate_categorized_analytics.py >> /var/log/parentpass_analytics.log 2>&1
```

## Running the API Server

### Development Server

Start the development server with hot reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

For production deployment:

```bash
# Production server (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With specific worker configuration
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

The API documentation will be at: http://localhost:8000/docs (Swagger UI)

## API Usage with cURL

### Authentication

All API endpoints require a Bearer token in the Authorization header:

### Health Check

```bash
curl -X GET "http://localhost:8000/api/health" \
  -H "Authorization: Bearer $PP_API_KEY"
```

### Session Management

**Create a new session:**
```bash
curl -X POST "http://localhost:8000/api/sessions" \
  -H "Authorization: Bearer $PP_API_KEY" \
  -H "Content-Type: application/json"
```

**Get session state:**
```bash
curl -X GET "http://localhost:8000/api/sessions/{session_id}" \
  -H "Authorization: Bearer $PP_API_KEY"
```

**Delete session:**
```bash
curl -X DELETE "http://localhost:8000/api/sessions/{session_id}" \
  -H "Authorization: Bearer $PP_API_KEY"
```

### Complete Example Workflow

```bash
# 1. Set your API key
export PP_API_KEY="your_api_key_here"

# 2. Create a session and capture session ID
SESSION_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/sessions" \
  -H "Authorization: Bearer $PP_API_KEY" \
  -H "Content-Type: application/json")

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Created session: $SESSION_ID"

# 3. Send a message
curl -X POST "http://localhost:8000/api/query" \
  -H "Authorization: Bearer $PP_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "message": "Show me the top engaged users this week"
  }' | jq '.'

# 4. Clean up session (best practice, but sessions will expire after 4 hours)
curl -X DELETE "http://localhost:8000/api/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $PP_API_KEY"
```

## Test API with recent data

A sample set of recent data and a test script has been provided so that the API can be tested without access to the live data.

With a server running (assumes localhost port 8000):

```bash
tar xvzf analytics_reports.tar.gz
python test_analytics_api.py
```