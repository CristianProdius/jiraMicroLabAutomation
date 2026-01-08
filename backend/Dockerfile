# Backend Dockerfile for Jira Feedback API
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install uvicorn[standard] psycopg2-binary asyncpg alembic email-validator bcrypt

# Copy application code
COPY src/ ./src/
COPY api/ ./api/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
