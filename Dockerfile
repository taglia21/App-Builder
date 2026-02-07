# Production Dockerfile for App-Builder
# Multi-stage build for smaller final image
#
# Uses requirements-prod.txt (lightweight, ~50 packages) instead of
# requirements.txt (full dev, ~100+ packages including torch/transformers/spacy).
# This cuts install time from 10+ min to ~1-2 min and image size by ~3.5GB.

# Stage 1: Builder - install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies needed for compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first for maximum Docker layer caching.
# This layer is rebuilt ONLY when requirements-prod.txt changes.
COPY requirements-prod.txt .

# Create virtual environment and install production dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Stage 2: Production - minimal runtime image
FROM python:3.12-slim AS production

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy application code
COPY --chown=appuser:appuser . .

# Remove unnecessary files from the image
RUN rm -rf tests/ .git/ .github/ *.md .env* __pycache__/ .pytest_cache/ \
    docs/ output/ scripts/ alembic/ nginx/ \
    requirements-dev.txt mypy.ini pyproject.toml \
    docker-compose*.yml tailwind.config.js

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "src.dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
