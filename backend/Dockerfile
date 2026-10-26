# =============================================================================
# SafeMap AI — Backend Dockerfile
# Multi-stage production container with non-root security execution
# =============================================================================

FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install minimal OS dependencies for geospatial libraries and health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pinned Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create an unprivileged non-root user and group for hardened security
RUN groupadd -g 10001 safemap && \
    useradd -u 10001 -g safemap -s /bin/bash -m safemap

# Copy application source code and entry points
COPY app/ ./app/
COPY evaluate_hyderabad_data_readiness.py .
COPY evaluate_model_readiness.py .
COPY run_data_curation.py .

# Create cache and runtime directories with appropriate permissions
RUN mkdir -p /app/cache /app/data /app/ml/models && \
    chown -R safemap:safemap /app

# Switch to unprivileged execution user
USER safemap

# Expose backend API port
EXPOSE 8000

# Docker health check probing the API health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Graceful startup using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
