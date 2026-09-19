import asyncio
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import load_config, monitor_config
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.domain_monitor import DomainMonitor
from src.monitors.security_monitor import SecurityMonitor
from src.monitors.ssl_monitor import SSLMonitor
from src.notifications.service import NotificationService

limiter = Limiter(key_func=get_remote_address)

# ── Optional API key ──────────────────────────────────────────────────────────
# POST /analyze makes this host run WHOIS, TLS and HTTP probes against whatever
# domain the caller names. docker-compose.yml binds the port to 127.0.0.1, but
# the Dockerfile's default CMD listens on 0.0.0.0, so anyone following the
# README can publish it. Setting DOMAINMATE_API_KEY requires the header;
# leaving it unset keeps the previous behaviour exactly.
API_KEY = os.environ.get("DOMAINMATE_API_KEY") or None
API_KEY_HEADER = "X-API-Key"

if API_KEY:
    logger.info(f"API key required on write endpoints (header: {API_KEY_HEADER})")
else:
    logger.warning(
        "DOMAINMATE_API_KEY is not set: /analyze and /notify/test are open to "
        "anyone who can reach this port"
    )


def require_api_key(x_api_key: str = Header(default=None, alias=API_KEY_HEADER)):
    """No key configured means no check, so existing deployments keep working."""
    if not API_KEY:
        return
    # compare_digest keeps the comparison time-independent of how much matched
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"A valid {API_KEY_HEADER} header is required",
        )

app = FastAPI(title="DomainMate API", version="0.5.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response

# The API honours the same monitors.<name> settings as the CLI, so a threshold
# tuned in config.yaml applies on both surfaces. A missing or broken config is
# not fatal here — the API still serves with built-in defaults.
try:
    _config = load_config()
except Exception as e:  # noqa: BLE001 - any failure falls back to defaults
    logger.warning(f"Running with default monitor settings: {e}")
    _config = {}

domain_monitor = DomainMonitor.from_config(monitor_config(_config, "domain"))
ssl_monitor = SSLMonitor.from_config(monitor_config(_config, "ssl"))
dns_monitor = DNSMonitor.from_config(monitor_config(_config, "dns"))
security_monitor = SecurityMonitor.from_config(monitor_config(_config, "security"))
blacklist_monitor = BlacklistMonitor.from_config(monitor_config(_config, "blacklist"))
notifier = NotificationService()

DOMAIN_PATTERN = re.compile(
    r'^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
)

class AnalyzeRequest(BaseModel):
    domain: str
    check_domain: bool = True
    check_ssl: bool = True
    check_dns: bool = True
    check_security: bool = True
    check_blacklist: bool = True

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        v = v.strip().lower()
        if not v:
            raise ValueError('Domain must be a non-empty string')
        if not DOMAIN_PATTERN.match(v):
            raise ValueError('Invalid domain format')
        return v

class TestNotificationRequest(BaseModel):
    title: str
    message: str
    level: Literal["info", "warning", "critical"] = "info"

@app.post("/analyze", dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def analyze_domain(request: Request, req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Run selected monitors for a domain.
    If critical issues are found, trigger notifications.
    Rate limited to 10 requests/minute per IP.
    """
    checks = []
    if req.check_domain:
        checks.append(("domain", domain_monitor.check_domain))
    if req.check_ssl:
        checks.append(("ssl", ssl_monitor.check_ssl))
    if req.check_dns:
        checks.append(("dns", dns_monitor.check_dns))
    if req.check_security:
        checks.append(("security", security_monitor.check_security))
    if req.check_blacklist:
        checks.append(("blacklist", blacklist_monitor.check_blacklist))

    # Monitors are blocking (whois/socket/dns): run them in threads to keep the event loop free
    outputs = await asyncio.gather(
        *(asyncio.to_thread(func, req.domain) for _, func in checks)
    )
    results = {name: output for (name, _), output in zip(checks, outputs, strict=True)}

    issues = []
    for monitor_name, res in results.items():
        if res.get("status") in ["critical", "error"]:
            issues.append(
                f"[{monitor_name.upper()}] Status: {res.get('status')} - "
                f"{res.get('message', 'Check details')}"
            )
        elif res.get("status") == "warning":
            issues.append(f"[{monitor_name.upper()}] Warning: {res.get('message', 'Expiring soon or missing config')}")

    if issues:
        summary = f"Issues found for {req.domain}:\n" + "\n".join(issues)
        has_critical = any(
            res.get("status") in ["critical", "error"] for res in results.values()
        )
        level = "critical" if has_critical else "warning"
        background_tasks.add_task(notifier.send_notification, f"DomainMate Alert: {req.domain}", summary, level)

    return {
        "domain": req.domain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "issues_found": len(issues)
    }

@app.post("/notify/test", dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def test_notification(request: Request, req: TestNotificationRequest, background_tasks: BackgroundTasks):
    """
    Test the notification configuration.
    Rate limited to 5 requests/minute per IP.
    """
    background_tasks.add_task(notifier.send_notification, req.title, req.message, req.level)
    return {"status": "queued", "message": "Notification task added to background queue."}

@app.get("/metrics")
def get_metrics():
    # Deliberately unauthenticated: the container HEALTHCHECK calls it, and it
    # discloses nothing about the monitored domains.
    return {
        "status": "healthy",
        "monitors_active": 5,
        "version": app.version,
        "auth_required": bool(API_KEY),
    }
