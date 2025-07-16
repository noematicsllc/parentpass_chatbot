# Multi-stage Docker build for ParentPass Chatbot API
# Stage 1: Builder - Install dependencies and generate BAML client
FROM python:3.13-slim AS builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management and baml-cli for generating BAML client
RUN pip install uv baml-cli

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

# Ensure scripts directory exists and is executable
RUN mkdir -p scripts

# Generate BAML client
RUN if [ -d "baml_src" ]; then \
    echo "BAML source found, generating client with baml-cli"; \
    baml-cli generate --from baml_src; \
    else \
    echo "No BAML source found, skipping client generation"; \
    fi

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim AS runtime

# Set runtime arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Azure SQL connectivity and cron
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    cron \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/app ./app
COPY --from=builder /app/baml_src ./baml_src
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY --from=builder /app/generate_categorized_analytics.py ./generate_categorized_analytics.py

# Copy generated baml_client
COPY --from=builder /app/baml_client ./baml_client

# Copy startup script
COPY --from=builder /app/scripts/startup.sh ./scripts/startup.sh

# Set up Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/analytics_reports \
    && chmod +x /app/scripts/startup.sh \
    && chown -R appuser:appuser /app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint to startup script
ENTRYPOINT ["/app/scripts/startup.sh"]

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"] 