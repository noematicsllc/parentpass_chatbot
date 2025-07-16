#!/bin/bash
set -e

echo "=== ParentPass Chatbot API Startup ==="

# Create analytics reports directory if it doesn't exist
mkdir -p /app/analytics_reports

# Check if analytics reports exist, if not generate them
if [ ! "$(ls -A /app/analytics_reports)" ]; then
    echo "No analytics reports found. Generating initial reports..."
    cd /app
    /app/.venv/bin/python generate_categorized_analytics.py
    echo "Initial analytics reports generated successfully"
else
    echo "Analytics reports directory exists and contains files"
fi

# Setup cron job for nightly analytics generation (3 AM UTC)
echo "Setting up cron job for nightly analytics generation..."
echo "0 3 * * * cd /app && /app/.venv/bin/python generate_categorized_analytics.py >> /app/logs/analytics_cron.log 2>&1" > /etc/cron.d/analytics-reports
echo "" >> /etc/cron.d/analytics-reports
chmod 0644 /etc/cron.d/analytics-reports
crontab /etc/cron.d/analytics-reports

# Start cron daemon in background
service cron start

echo "Starting FastAPI application..."

# Execute the command passed to the container (uvicorn)
exec "$@" 