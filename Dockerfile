# Privasee BI SaaS - Production Dockerfile
# Multi-stage build for optimal image size and security

# =============================================================================
# Stage 1: Builder - Install dependencies and compile
# =============================================================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim

# Metadata
LABEL maintainer="Privasee Team"
LABEL version="1.0.0"
LABEL description="Privasee BI SaaS Application"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_ENV=production \
    WORKERS=4

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    unixodbc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r privasee && \
    useradd -r -g privasee -u 1000 -m -s /bin/bash privasee

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=privasee:privasee . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/instance && \
    chown -R privasee:privasee /app/data /app/logs /app/instance

# Switch to non-root user
USER privasee

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health/liveness || exit 1

# Create entrypoint script
COPY --chown=privasee:privasee docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - can be overridden
CMD ["gunicorn", "--config", "gunicorn_config.py", "wsgi:application"]
