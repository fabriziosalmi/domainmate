import yaml
import asyncio
import argparse
import sys
import os
import aiohttp
from loguru import logger
from src.monitors.domain_monitor import DomainMonitor
from src.monitors.ssl_monitor import SSLMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.security_monitor import SecurityMonitor
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.notifications.service import NotificationService
from src.reporting.html_generator import HTMLGenerator
import random
from datetime import datetime, timedelta
from typing import Optional

def clean_domain(raw_domain: str) -> str:
    """
    Smartly extract hostname from URLs or dirty inputs.
    e.g. 'https://www.google.com/foo' -> 'www.google.com'
    """
    # Remove protocol
    if "://" in raw_domain:
        raw_domain = raw_domain.split("://")[1]
    
    # Remove path/params
    raw_domain = raw_domain.split("/")[0].split("?")[0]
    
    # Remove port if present
    if ":" in raw_domain:
        raw_domain = raw_domain.split(":")[0]
        
    return raw_domain.strip().lower()

def get_parent_domain(domain: str) -> str:
    """
    Extracts the parent domain (SLD+TLD) from a subdomain.
    """
    parts = domain.split('.')
    if len(parts) > 2:
        return f"{parts[-2]}.{parts[-1]}"
    return domain

def get_connectable_hostname(domain: str) -> Optional[str]:
    """
    Try to find a resolvable hostname. 
    1. Try exact domain.
    2. Try www.domain.
    Uses RobustResolver to bypass local DNS issues.
    """
    from src.utils.dns_helpers import RobustResolver
    resolver = RobustResolver(timeout=2.0)
    
    try:
        resolver.get_ip(domain)
        return domain
    except Exception:
        try:
            www = f"www.{domain}"
            resolver.get_ip(www)
            logger.info(f"Root {domain} not reachable, falling back to {www}")
            return www
        except Exception:
            return None
 

def get_demo_data():
    """Generates fake data for demo purposes."""
    domains = [
        "prod-api.com", "staging-app.net", "legacy-system.org", 
        "marketing-site.com", "internal-tool.io"
    ]
    results = []
    
    for d in domains:
        # 1. Domain
        days = random.choice([5, 45, 200, 15])
        status = "ok"
        if days < 7: status = "critical"
        elif days < 30: status = "warning"
        
        results.append({
            "domain": d, "monitor": "domain", "status": status,
            "days_until_expiry": days, "expiration_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
            "message": f"Expires in {days} days"
        })

        # 2. SSL (one expired cert to showcase that state)
        ssl_days = -12 if d == "legacy-system.org" else random.choice([3, 100, 365])
        ssl_status = "ok"
        if ssl_days < 7: ssl_status = "critical"
        elif ssl_days < 30: ssl_status = "warning"
        results.append({
            "domain": d, "monitor": "ssl", "status": ssl_status,
            "days_until_expiry": ssl_days, "expiration_date": (datetime.now() + timedelta(days=ssl_days)).strftime("%Y-%m-%d"),
            "message": f"Expired {-ssl_days} days ago" if ssl_days < 0 else f"Expires in {ssl_days} days"
        })

        # 3. DNS
        results.append({
            "domain": d, "monitor": "dns", "status": "ok",
            "message": "SPF and DMARC present",
            "details": {"spf": "v=spf1 include:_spf.google.com ~all", "dmarc": "v=DMARC1; p=reject;"}
        })
        
        # 4. Blacklist (One failure)
        if d == "legacy-system.org":
            results.append({
                "domain": d, "monitor": "blacklist", "status": "critical",
                "message": "Listed in 2 RBLs (Spamhaus, SORBS)",
                "listed_in": ["zen.spamhaus.org", "dnsbl.sorbs.net"]
            })
        else:
             results.append({
                "domain": d, "monitor": "blacklist", "status": "ok",
                "message": "Clean"
            })

    return results

async def main():
    parser = argparse.ArgumentParser(description="DomainMate CLI")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--notify", action="store_true", help="Enable notifications")
    parser.add_argument("--demo", action="store_true", help="Run with mock data for demonstration")
    args = parser.parse_args()

    if args.demo:
        logger.info("Running in DEMO mode. Generating mock data...")
        reporter = HTMLGenerator(output_dir="reports")
        all_results = get_demo_data()
        report_path = reporter.generate(all_results)
        logger.success(f"Demo Report generated at {report_path}")
        return

    # Load Config
    config_path = os.environ.get("DOMAINMATE_CONFIG_FILE", args.config)
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)

    domains = config.get("domains", [])
    if not domains:
        logger.warning("No domains found in config.")
        sys.exit(0)

    # Init Services
    domain_monitor = DomainMonitor()
    ssl_monitor = SSLMonitor()
    dns_monitor = DNSMonitor()
    security_monitor = SecurityMonitor()
    blacklist_monitor = BlacklistMonitor()
    notifier = NotificationService()
    reporter = HTMLGenerator(output_dir=config.get("reports", {}).get("output_dir", "reports"))
    monitors_cfg = config.get("monitors", {})

    all_results = []
    
    logger.info(f"Starting check for {len(domains)} domains...")

    for raw_domain in domains:
        domain = clean_domain(raw_domain)
        logger.info(f"Checking {domain}...")
        
        # Determine best target for connection-based checks (SSL, Security)
        connectable_host = get_connectable_hostname(domain)
        parent_domain = get_parent_domain(domain)
        
        # We sequentially check for now to be gentle, could be async gathered
        # 1. Domain (WHOIS always uses root/parent)
        if monitors_cfg.get("domain", {}).get("enabled", False):
            try:
                # Use parent domain for WHOIS to avoid "No whois server found for subdomain" errors
                check_target = parent_domain
                res = domain_monitor.check_domain(check_target)
                res["domain"] = domain # Keep original label
                if check_target != domain:
                    res["message"] = f"(Parent: {check_target}) {res.get('message', '')}"
                all_results.append(res)
            except Exception as e:
                logger.error(f"Domain monitor failed for {domain}: {e}")

        # 2. SSL (Use connectable host)
        if monitors_cfg.get("ssl", {}).get("enabled", False):
            if connectable_host:
                res = ssl_monitor.check_ssl(connectable_host)
                if connectable_host != domain:
                    res["message"] = f"(Checked {connectable_host}) {res.get('message', '')}"
                res["domain"] = domain
                all_results.append(res)
            else:
                logger.warning(f"Skipping SSL check for {domain}: DNS resolution failed.")
                all_results.append({
                    "domain": domain,
                    "monitor": "ssl",
                    "status": "critical",
                    "message": "DNS Resolution Failed",
                    "details": {"error": "Could not resolve hostname or www subdomain"}
                })
        
        # 3. DNS (Always root/parent)
        if monitors_cfg.get("dns", {}).get("enabled", False):
            check_target = parent_domain
            res = dns_monitor.check_dns(check_target)
            res["domain"] = domain
            if check_target != domain:
                 res["message"] = f"(Parent: {check_target}) {res.get('message', '')}"
            all_results.append(res)

        # 4. Security (Use connectable host)
        if monitors_cfg.get("security", {}).get("enabled", False):
            if connectable_host:
                res = security_monitor.check_security(connectable_host)
                if connectable_host != domain:
                    res["message"] = f"(Checked {connectable_host}) {res.get('message', '')}"
                res["domain"] = domain
                all_results.append(res)
            else:
                 logger.warning(f"Skipping Security check for {domain}: DNS resolution failed.")
                 all_results.append({
                    "domain": domain,
                    "monitor": "security",
                    "status": "critical",
                    "message": "DNS Resolution Failed",
                    "details": {"error": "Could not resolve hostname or www subdomain"}
                })

        # 5. Blacklist (Always root/IP mainly)
        if monitors_cfg.get("blacklist", {}).get("enabled", False):
            res = blacklist_monitor.check_blacklist(domain)
            res["domain"] = domain
            all_results.append(res)

    # Generate Report
    report_path = reporter.generate(all_results)
    logger.success(f"Report generated at {report_path}")

    timeout = aiohttp.ClientTimeout(total=15)

    # Heartbeat (Dead Man's Switch)
    heartbeat_url = config.get("heartbeat_url")
    if heartbeat_url:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(heartbeat_url) as resp:
                    resp.raise_for_status()
            logger.info("Heartbeat ping sent.")
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

    # JSON API Upload
    api_url = config.get("api_url")
    if api_url:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(api_url, json=all_results) as resp:
                    resp.raise_for_status()
            logger.info(f"JSON Report uploaded to {api_url}")
        except Exception as e:
            logger.error(f"Failed to upload JSON report: {e}")

    # Notifications
    if args.notify:
        issues = [r for r in all_results if r.get("status") in ["warning", "critical", "error"]]
        if not issues:
            logger.info("No issues found, skipping notification.")
        else:
            level = "critical" if any(r.get("status") in ["critical", "error"] for r in issues) else "warning"
            affected = sorted({r.get("domain", "unknown") for r in issues})
            msg = (
                f"Found {len(issues)} issue(s) requiring attention.\n"
                f"Domains: {', '.join(affected)}\n"
                f"Check report for details."
            )
            await notifier.send_notification("DomainMate Alert", msg, level)

if __name__ == "__main__":
    asyncio.run(main())
