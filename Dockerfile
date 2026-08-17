FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for dependency caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY packages/ ./packages/
COPY apps/ ./apps/
COPY schemas/ ./schemas/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for HTTP API
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "uvicorn", "apps.domain_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
