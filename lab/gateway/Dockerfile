FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose API port
EXPOSE 8080

# Run the gateway
CMD ["python", "src/gateway.py"]
