import asyncio
import argparse
import json
import sys
import aiohttp
from urllib.parse import urlparse
from loguru import logger
from src.notifications.service import NotificationService
from src.reporting.html_generator import HTMLGenerator
from src.config import load_config, report_setting
from src.scanner import build_monitors, scan_all
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from src.constants import (
    TIMEOUT_CLI_HTTP, DEFAULT_CONCURRENCY,
    STATUS_WARNING, STATUS_CRITICAL, STATUS_ERROR,
    EXIT_OK, EXIT_WARNING, EXIT_CRITICAL, EXIT_ERROR,
)

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

class _ArgumentParser(argparse.ArgumentParser):
    """
    argparse exits with 2 on a usage error, which would be indistinguishable
    from "critical findings". Usage errors are operational, so they use
    EXIT_ERROR like every other failure to run.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_ERROR, f"{self.prog}: error: {message}\n")

def compute_exit_code(results: list, fail_on: str) -> int:
    """
    Map scan results to a process exit code so CI can gate on findings.

    never    - always EXIT_OK; the scan result never fails the build (default,
               so existing pipelines keep the behaviour they have today)
    warning  - EXIT_WARNING on warnings, EXIT_CRITICAL on critical/error
    critical - EXIT_CRITICAL on critical/error only; warnings do not fail
    """
    if fail_on == "never":
        return EXIT_OK

    statuses = {r.get("status") for r in results}

    if statuses & {STATUS_CRITICAL, STATUS_ERROR}:
        return EXIT_CRITICAL
    if fail_on == "warning" and STATUS_WARNING in statuses:
        return EXIT_WARNING
    return EXIT_OK

def emit_json(results: list) -> None:
    """
    Write the full result set to stdout. Logs go to stderr (loguru's default),
    so stdout stays clean enough to pipe into jq.
    """
    json.dump(results, sys.stdout, indent=2, default=str, ensure_ascii=False)
    sys.stdout.write("\n")

def _validate_url(url: str, label: str) -> bool:
    """
    Validate that a URL uses http or https and has a non-empty hostname.
    Logs a warning and returns False if the URL is rejected.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"{label} URL rejected: scheme '{parsed.scheme}' is not http/https")
            return False
        if not parsed.hostname:
            logger.warning(f"{label} URL rejected: missing hostname")
            return False
        return True
    except Exception as e:
        logger.warning(f"{label} URL validation error: {e}")
        return False

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
            "days_until_expiry": days, "expiration_date": (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d"),
            "message": f"Expires in {days} days"
        })

        # 2. SSL (one expired cert to showcase that state)
        ssl_days = -12 if d == "legacy-system.org" else random.choice([3, 100, 365])
        ssl_status = "ok"
        if ssl_days < 7: ssl_status = "critical"
        elif ssl_days < 30: ssl_status = "warning"
        results.append({
            "domain": d, "monitor": "ssl", "status": ssl_status,
            "days_until_expiry": ssl_days, "expiration_date": (datetime.now(timezone.utc) + timedelta(days=ssl_days)).strftime("%Y-%m-%d"),
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

async def main() -> int:
    parser = _ArgumentParser(
        description="DomainMate CLI",
        epilog=(
            "Exit codes: 0 no findings above the threshold, 1 warnings, "
            "2 critical or error findings, 3 could not run."
        ),
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--notify", action="store_true", help="Enable notifications")
    parser.add_argument("--demo", action="store_true", help="Run with mock data for demonstration")
    parser.add_argument(
        "--fail-on",
        choices=["never", "warning", "critical"],
        default="never",
        help=(
            "Exit non-zero when the scan finds issues at this level or worse. "
            "Default: never, so the exit code stays 0 as it always has."
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        metavar="N",
        help=(
            f"How many checks may run at once (default: {DEFAULT_CONCURRENCY}). "
            f"Lower it if a registry or RBL rate-limits you."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Write the full result set as JSON to stdout (logs stay on stderr)",
    )
    args = parser.parse_args()

    if args.demo:
        logger.info("Running in DEMO mode. Generating mock data...")
        reporter = HTMLGenerator(output_dir="reports")
        all_results = get_demo_data()
        report_path = reporter.generate(all_results)
        logger.success(f"Demo Report generated at {report_path}")
        if args.emit_json:
            emit_json(all_results)
        return compute_exit_code(all_results, args.fail_on)

    # Load Config
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return EXIT_ERROR

    domains = config.get("domains", [])
    if not domains:
        logger.warning("No domains found in config.")
        return EXIT_OK

    # Init Services — each monitor reads its own monitors.<name> section
    monitors = build_monitors(config)
    notifier = NotificationService()
    reporter = HTMLGenerator(output_dir=report_setting(config, "output_dir", "reports"))

    all_results = await scan_all(domains, monitors, config, args.concurrency)

    # Generate Report
    report_path = reporter.generate(all_results)
    logger.success(f"Report generated at {report_path}")

    timeout = aiohttp.ClientTimeout(total=TIMEOUT_CLI_HTTP)

    # Heartbeat (Dead Man's Switch)
    heartbeat_url = config.get("heartbeat_url")
    if heartbeat_url:
        if _validate_url(heartbeat_url, "Heartbeat"):
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
        if _validate_url(api_url, "API upload"):
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

    if args.emit_json:
        emit_json(all_results)

    exit_code = compute_exit_code(all_results, args.fail_on)
    if exit_code != EXIT_OK:
        logger.warning(f"Exiting with code {exit_code} (--fail-on {args.fail_on})")
    return exit_code

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
