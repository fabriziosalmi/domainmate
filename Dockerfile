# Build Stage
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Runtime Stage
FROM python:3.12-slim

WORKDIR /app

# curl is used by the HEALTHCHECK below
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# Unprivileged runtime account. The UID is fixed so a bind-mounted reports/
# directory can be chowned to a predictable owner on the host.
RUN groupadd --gid 10001 domainmate \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin domainmate

COPY . .

# Application code stays root-owned and read-only to the runtime account.
# Only the two directories the app actually writes to are handed over:
#   reports/        — generated HTML and JSON reports
#   src/templates/  — HTMLGenerator rewrites report.html on every run; once that
#                     is fixed this directory can go back to being read-only.
RUN mkdir -p reports src/templates \
    && chown -R 10001:10001 reports src/templates

EXPOSE 8000

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1

USER 10001:10001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/metrics || exit 1

# Default command: Run the API.
# Override to run CLI: docker run ... python src/cli.py
CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
