# API

DomainMate includes a FastAPI-based REST API for programmatic access to monitoring capabilities.

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
    "message": "SPF and DMARC present",
    "details": {
      "spf": "v=spf1 include:_spf.google.com ~all",
      "dmarc": "v=DMARC1; p=reject;"
    }
  },
  "security": {
    "monitor": "security",
    "status": "warning",
    "message": "2 Security Issues",
    "details": {
      "missing_headers": ["X-Frame-Options"]
    }
  },
  "blacklist": {
    "monitor": "blacklist",
    "status": "ok",
    "message": "Clean"
  }
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

**Example with JavaScript:**
```javascript
fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    domain: 'example.com',
    check_domain: true,
    check_ssl: true,
    check_dns: true,
    check_security: true,
    check_blacklist: true
  })
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### POST `/test-notification`

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
  "status": "sent",
  "channels": ["telegram", "email"],
  "timestamp": "2025-01-03T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/test-notification" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Alert",
    "message": "Testing DomainMate notifications",
    "level": "warning"
  }'
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-03T12:00:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

## Authentication

### Basic Authentication (Optional)

Add authentication middleware:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "secret")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
        )
    return credentials.username

@app.post("/analyze", dependencies=[Depends(authenticate)])
async def analyze_domain(req: AnalyzeRequest):
    # ...
```

### API Key Authentication (Recommended)

```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.post("/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_domain(req: AnalyzeRequest):
    # ...
```

**Usage:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com"}'
```

## Integration Examples

### Monitoring Dashboard

Build a real-time monitoring dashboard:

```python
import asyncio
import aiohttp

async def monitor_domains(domains):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for domain in domains:
            task = session.post(
                "http://localhost:8000/analyze",
                json={"domain": domain}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        results = [await r.json() for r in responses]
        return results

domains = ["example.com", "mysite.io", "another.com"]
results = asyncio.run(monitor_domains(domains))

for result in results:
    print(f"Domain: {result['domain']['domain']}")
    print(f"Status: {result['domain']['status']}")
```

### Webhook Handler

Trigger scans from webhooks:

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/webhook/domain-scan', methods=['POST'])
def domain_scan_webhook():
    data = request.json
    domain = data.get('domain')
    
    # Trigger DomainMate scan
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"domain": domain}
    )
    
    results = response.json()
    
    # Process results
    if results['ssl']['status'] == 'critical':
        # Send alert
        send_critical_alert(domain, results)
    
    return jsonify({"status": "processed"})
```

### Slack Bot Integration

Create a Slack bot that checks domains:

```python
from slack_bolt import App
import requests

app = App(token="xoxb-your-token")

@app.command("/checkdomain")
def check_domain_command(ack, say, command):
    ack()
    domain = command['text']
    
    # Call DomainMate API
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"domain": domain}
    )
    
    results = response.json()
    
    # Format response
    message = f"*Domain Check: {domain}*\n"
    message += f"• Domain: {results['domain']['status']}\n"
    message += f"• SSL: {results['ssl']['status']}\n"
    message += f"• Security: {results['security']['status']}\n"
    
    say(message)

if __name__ == "__main__":
    app.start(3000)
```

### Automated Remediation

Automatically fix issues:

```python
import requests

def check_and_remediate(domain):
    # Scan domain
    response = requests.post(
        "http://localhost:8000/analyze",
        json={"domain": domain}
    )
    
    results = response.json()
    
    # Check SSL status
    if results['ssl']['days_until_expiry'] < 30:
        print(f"SSL expiring soon for {domain}")
        # Trigger certificate renewal
        trigger_cert_renewal(domain)
    
    # Check security headers
    if results['security']['status'] != 'ok':
        print(f"Security issues for {domain}")
        # Update CDN configuration
        update_security_headers(domain)
    
    return results
```

## Rate Limiting

Implement rate limiting to prevent abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_domain(request: Request, req: AnalyzeRequest):
    # ...
```

## CORS Configuration

Enable CORS for web applications:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Deployment

### Docker

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
docker build -t domainmate-api .
docker run -p 8000:8000 domainmate-api
```

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./reports:/app/reports
```

### Kubernetes

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: domainmate-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: domainmate-api
  template:
    metadata:
      labels:
        app: domainmate-api
    spec:
      containers:
      - name: api
        image: domainmate-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: domainmate-secrets
              key: github-token
---
apiVersion: v1
kind: Service
metadata:
  name: domainmate-api
spec:
  selector:
    app: domainmate-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Performance

### Caching

Implement caching for frequent requests:

```python
from functools import lru_cache
import time

cache = {}

@app.post("/analyze")
async def analyze_domain(req: AnalyzeRequest):
    cache_key = f"{req.domain}:{req.check_domain}:{req.check_ssl}"
    
    # Check cache
    if cache_key in cache:
        cached_time, cached_result = cache[cache_key]
        if time.time() - cached_time < 3600:  # 1 hour cache
            return cached_result
    
    # Perform analysis
    results = perform_analysis(req)
    
    # Store in cache
    cache[cache_key] = (time.time(), results)
    
    return results
```

### Async Processing

Use background tasks for long-running operations:

```python
from fastapi import BackgroundTasks

async def process_domain_async(domain: str):
    # Long-running task
    results = await analyze_domain(domain)
    # Store results
    # Send notifications
    pass

@app.post("/analyze-async")
async def analyze_async(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(process_domain_async, req.domain)
    return {"job_id": job_id, "status": "processing"}
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn api:app --port 8001
```

### Module Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/domainmate

# Or run from correct directory
cd /path/to/domainmate
uvicorn api.api:app
```

### CORS Errors

Add CORS middleware as shown above, or test with:

```bash
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/analyze
```

## Next Steps

- Automate with [CI/CD Integration](/guide/ci-cd)
- Learn about architecture in [Reference](/reference/architecture)
- See [Troubleshooting](/reference/troubleshooting) for common issues
