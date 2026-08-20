# Microservice Container Image for RCAI Incident Simulation
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     curl     && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir .

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1

# Default startup using entrypoint or service name env
CMD ["sh", "-c", "uvicorn simulator.services.${SERVICE_NAME//-/_}:app --host 0.0.0.0 --port ${SERVICE_PORT}"]
