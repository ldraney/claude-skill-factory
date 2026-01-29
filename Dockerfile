FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Default command (override in docker-compose)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
