FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared common module
COPY --chown=appuser:appuser ../common /app/lab/common

# Copy source code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser __init__.py .

# Create data directory
RUN mkdir -p /data && chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

# Expose OTLP HTTP port
EXPOSE 4318

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:4318/health', timeout=2)" || exit 1

# Run the collector
CMD ["python", "src/collector.py"]
