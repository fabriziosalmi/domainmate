# API

DomainMate includes a FastAPI-based REST API for programmatic access to monitoring capabilities.

## Authentication

`POST /analyze` makes this host run WHOIS, TLS and HTTP probes against whatever
domain the caller names. `docker-compose.yml` binds the port to `127.0.0.1`,
but the Dockerfile's default command listens on `0.0.0.0`, so anyone following
the README can publish it.

Set `DOMAINMATE_API_KEY` to require a header on the write endpoints:

```bash
export DOMAINMATE_API_KEY="$(openssl rand -hex 32)"
```

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: $DOMAINMATE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}'
```

Without the header, or with the wrong value, the request is rejected with
`401`. Leaving the variable unset keeps both endpoints open exactly as before,
and logs a warning at startup saying so.

`GET /metrics` stays unauthenticated: the container healthcheck calls it, and it
discloses nothing about the monitored domains. It does report whether the key is
in force:

```json
{ "status": "healthy", "monitors_active": 5, "version": "0.5.0", "auth_required": true }
```

Rate limiting applies either way: 10 requests a minute per IP on `/analyze`,
5 on `/notify/test`.

## Overview

The API allows you to:
- Trigger on-demand domain analysis
- Check individual monitors
- Integrate with external systems
- Build custom dashboards
- Automate workflows

## Starting the API Server

### Development Mode

```bash
cd api
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker

```bash
docker run -p 8000:8000 domainmate-api
```

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Endpoints

### POST `/analyze`

Analyze a domain with selected monitors.

**Request:**
```json
{
  "domain": "example.com",
  "check_domain": true,
  "check_ssl": true,
  "check_dns": true,
  "check_security": true,
  "check_blacklist": true
}
```

**Response:**
```json
{
  "domain": "example.com",
  "timestamp": "2025-01-03T12:00:00",
  "results": {
    "domain": {
      "monitor": "domain",
      "status": "ok",
      "expiration_date": "2026-05-15",
      "days_until_expiry": 502,
      "registrar": "GoDaddy.com, LLC"
    },
    "ssl": {
      "monitor": "ssl",
      "status": "ok",
      "expiration_date": "2025-06-15",
      "days_until_expiry": 163,
      "issuer": "Let's Encrypt"
    },
    "dns": {
      "monitor": "dns",
      "status": "ok",
      "spf": {"status": "present", "record": "v=spf1 include:_spf.google.com ~all"},
      "dmarc": {"status": "present", "record": "v=DMARC1; p=reject;"}
    },
    "security": {
      "monitor": "security",
      "status": "warning",
      "message": "2 Security Issues",
      "details": ["Missing HSTS (OWASP A05)", "Missing CSP (OWASP A05 - XSS Risk)"]
    },
    "blacklist": {
      "monitor": "blacklist",
      "status": "ok",
      "message": "Not listed in any common RBL"
    }
  },
  "issues_found": 1
}
```

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "check_domain": true,
    "check_ssl": true,
    "check_dns": true,
    "check_security": true,
    "check_blacklist": true
  }'
```

**Example with Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "domain": "example.com",
        "check_domain": True,
        "check_ssl": True,
        "check_dns": True,
        "check_security": True,
        "check_blacklist": True
    }
)

results = response.json()
print(results)
```

### POST `/notify/test`

Test notification channels.

**Request:**
```json
{
  "title": "Test Alert",
  "message": "This is a test notification from DomainMate API",
  "level": "info"
}
```

**Levels:** `info`, `warning`, `critical`

**Response:**
```json
{
  "status": "queued",
  "message": "Notification task added to background queue."
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/notify/test" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Alert",
    "message": "Testing DomainMate notifications",
    "level": "warning"
  }'
```

### GET `/metrics`

Returns basic health and status information.

**Response:**
```json
{
  "status": "healthy",
  "monitors_active": 5,
  "version": "0.4.0"
}
```

**Example:**
```bash
curl http://localhost:8000/metrics
```

## Deployment

### Docker

**Build and run:**
```bash
docker build -t domainmate-api .
docker run -p 8000:8000 \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" \
  -v $(pwd)/config.yaml:/app/config.yaml \
  domainmate-api
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn api.api:app --port 8001
```

### Module Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/domainmate

# Or run from correct directory
cd /path/to/domainmate
uvicorn api.api:app
```

## Next Steps

- Automate with [CI/CD Integration](/guide/ci-cd)
- Learn about architecture in [Reference](/reference/architecture)
- See [Troubleshooting](/reference/troubleshooting) for common issues
