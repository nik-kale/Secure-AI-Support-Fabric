FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose UI port
EXPOSE 3000

# Run the dashboard
CMD ["python", "src/app.py"]
