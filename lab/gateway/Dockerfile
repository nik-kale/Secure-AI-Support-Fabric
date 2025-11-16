FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared common module
COPY --chown=appuser:appuser ../common /app/lab/common

# Copy source code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser __init__.py .

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=2)" || exit 1

# Run the gateway
CMD ["python", "src/gateway.py"]
