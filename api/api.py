from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from loguru import logger

from src.monitors.domain_monitor import DomainMonitor
from src.monitors.ssl_monitor import SSLMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.security_monitor import SecurityMonitor
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.notifications.service import NotificationService

app = FastAPI(title="DomainMate API", version="1.0.0")

# Initialize Services
domain_monitor = DomainMonitor()
ssl_monitor = SSLMonitor()
dns_monitor = DNSMonitor()
security_monitor = SecurityMonitor()
blacklist_monitor = BlacklistMonitor()
notifier = NotificationService()

class AnalyzeRequest(BaseModel):
    domain: str
    check_domain: bool = True
    check_ssl: bool = True
    check_dns: bool = True
    check_security: bool = True
    check_blacklist: bool = True

class TestNotificationRequest(BaseModel):
    title: str
    message: str
    level: str = "info" # info, warning, critical

@app.post("/analyze")
async def analyze_domain(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Run selected monitors for a domain.
    If critical issues are found, trigger notifications.
    """
    results = {}
    
    # 1. Domain Check
    if req.check_domain:
        results["domain"] = domain_monitor.check_domain(req.domain)
    
    # 2. SSL Check
    if req.check_ssl:
        results["ssl"] = ssl_monitor.check_ssl(req.domain)

    # 3. DNS Check
    if req.check_dns:
        results["dns"] = dns_monitor.check_dns(req.domain)

    # 4. Security Check
    if req.check_security:
        results["security"] = security_monitor.check_security(req.domain)

    # 5. Blacklist Check
    if req.check_blacklist:
        results["blacklist"] = blacklist_monitor.check_blacklist(req.domain)

    # Check for critical/warning issues to notify
    issues = []
    
    # Helper to check status
    for monitor_name, res in results.items():
        if res.get("status") in ["critical", "error"]:
            issues.append(f"[{monitor_name.upper()}] Status: {res.get('status')} - {res.get('message', 'Check details')}")
        elif res.get("status") == "warning":
             issues.append(f"[{monitor_name.upper()}] Warning: {res.get('message', 'Expiring soon or missing config')}")

    if issues:
        # Send Notification in background
        summary = f"Issues found for {req.domain}:\n" + "\n".join(issues)
        level = "critical" if any("critical" in i or "error" in i for i in issues) else "warning"
        background_tasks.add_task(notifier.send_notification, f"DomainMate Alert: {req.domain}", summary, level)

    return {
        "domain": req.domain,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "issues_found": len(issues)
    }

@app.post("/notify/test")
async def test_notification(req: TestNotificationRequest, background_tasks: BackgroundTasks):
    """
    Test the notification configuration.
    """
    background_tasks.add_task(notifier.send_notification, req.title, req.message, req.level)
    return {"status": "queued", "message": "Notification task added to background queue."}

@app.get("/metrics")
def get_metrics():
    """
    Exposing Prometheus-style metrics (mocked/simple for now).
    """
    return {
        "status": "healthy",
        "monitors_active": 4,
        "version": "1.0.0"
    }

from datetime import datetime
