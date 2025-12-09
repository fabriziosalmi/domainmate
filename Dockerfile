# Build Stage
# Build Stage
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Runtime Stage
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for compilation of some libs sometimes, but mostly for clean env)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

COPY . .

# Create reports dir
RUN mkdir -p reports

# Expose API port
EXPOSE 8000

ENV PYTHONPATH=/app

# Default command: Run the API. 
# Override to run CLI: docker run ... python src/cli.py
CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
