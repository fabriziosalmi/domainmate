import asyncio
import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.monitors.domain_monitor import DomainMonitor
from src.monitors.ssl_monitor import SSLMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.security_monitor import SecurityMonitor
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.notifications.service import NotificationService

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="DomainMate API", version="0.4.0")
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

domain_monitor = DomainMonitor()
ssl_monitor = SSLMonitor()
dns_monitor = DNSMonitor()
security_monitor = SecurityMonitor()
blacklist_monitor = BlacklistMonitor()
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

@app.post("/analyze")
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
    results = {name: output for (name, _), output in zip(checks, outputs)}

    issues = []
    for monitor_name, res in results.items():
        if res.get("status") in ["critical", "error"]:
            issues.append(f"[{monitor_name.upper()}] Status: {res.get('status')} - {res.get('message', 'Check details')}")
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

@app.post("/notify/test")
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
    return {
        "status": "healthy",
        "monitors_active": 5,
        "version": app.version
    }
