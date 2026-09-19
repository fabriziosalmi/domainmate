"""
Runs the monitors over the configured domains.

The checks are blocking (WHOIS, sockets, DNS), so they run in worker threads
and are gathered concurrently — the same pattern the API has always used for a
single domain, applied here to the whole scan. A semaphore bounds how many run
at once so a large domain list does not hammer registries and RBL servers.

Results keep the order of the config file, and within a domain the order the
monitors are declared here, so two runs over the same config produce the same
report.json regardless of which check happened to finish first.
"""

import asyncio
from functools import partial

from loguru import logger

from src.config import monitor_enabled
from src.constants import DEFAULT_CONCURRENCY, DEFAULT_TLS_PORT, STATUS_CRITICAL
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.domain_monitor import DomainMonitor
from src.monitors.security_monitor import SecurityMonitor
from src.monitors.ssl_monitor import SSLMonitor

#: Report order within a domain, kept stable across runs.
MONITOR_ORDER = ("domain", "ssl", "dns", "security", "blacklist")


def build_monitors(config: dict) -> dict:
    """Build every monitor from its ``monitors.<name>`` section."""
    from src.config import monitor_config
    return {
        "domain": DomainMonitor.from_config(monitor_config(config, "domain")),
        "ssl": SSLMonitor.from_config(monitor_config(config, "ssl")),
        "dns": DNSMonitor.from_config(monitor_config(config, "dns")),
        "security": SecurityMonitor.from_config(monitor_config(config, "security")),
        "blacklist": BlacklistMonitor.from_config(monitor_config(config, "blacklist")),
    }


def _unresolved_result(domain: str, monitor: str) -> dict:
    return {
        "domain": domain,
        "monitor": monitor,
        "status": STATUS_CRITICAL,
        "message": "DNS Resolution Failed",
        "details": {"error": "Could not resolve hostname or www subdomain"},
    }


async def _call(sem: asyncio.Semaphore, func, *args):
    """Run a blocking check in a worker thread, bounded by the semaphore."""
    async with sem:
        return await asyncio.to_thread(func, *args)


async def scan_domain(raw_domain: str, monitors: dict, config: dict,
                      sem: asyncio.Semaphore) -> list:
    """
    Run the enabled monitors for one domain and return their results in
    MONITOR_ORDER.
    """
    from src.cli import get_connectable_hostname, get_parent_domain, split_host_port

    # Only the TLS check cares about a port; WHOIS, DNS and the RBLs all want
    # the bare hostname.
    domain, port = split_host_port(raw_domain)
    parent = get_parent_domain(domain)
    logger.info(f"Checking {domain}...")

    # Resolution decides the target for the connection-based checks, so it has
    # to finish before those are scheduled.
    connectable = await _call(sem, get_connectable_hostname, domain)

    # (name, target, label prefix) for the checks that can actually run
    planned = []

    if monitor_enabled(config, "domain"):
        planned.append(("domain", monitors["domain"].check_domain, parent,
                        f"(Parent: {parent}) " if parent != domain else ""))

    if monitor_enabled(config, "ssl") and connectable:
        if port is not None:
            label = f"(Checked {connectable}:{port}) "
        else:
            label = f"(Checked {connectable}) " if connectable != domain else ""
        planned.append((
            "ssl",
            partial(monitors["ssl"].check_ssl, port=port or DEFAULT_TLS_PORT),
            connectable,
            label,
        ))

    if monitor_enabled(config, "dns"):
        planned.append(("dns", monitors["dns"].check_dns, parent,
                        f"(Parent: {parent}) " if parent != domain else ""))

    if monitor_enabled(config, "security") and connectable:
        planned.append(("security", monitors["security"].check_security, connectable,
                        f"(Checked {connectable}) " if connectable != domain else ""))

    if monitor_enabled(config, "blacklist"):
        planned.append(("blacklist", monitors["blacklist"].check_blacklist, domain, ""))

    outputs = await asyncio.gather(
        *(_call(sem, func, target) for _, func, target, _ in planned),
        return_exceptions=True,
    )

    by_name = {}
    for (name, _, _, prefix), output in zip(planned, outputs, strict=True):
        if isinstance(output, Exception):
            # BaseMonitor.check() already turns failures into error results, so
            # reaching here means something outside it broke.
            logger.error(f"{name} monitor failed for {domain}: {output}")
            continue
        output["domain"] = domain
        if prefix:
            output["message"] = f"{prefix}{output.get('message', '')}"
        by_name[name] = output

    # Checks that could not run because the hostname did not resolve
    for name in ("ssl", "security"):
        if monitor_enabled(config, name) and not connectable:
            logger.warning(f"Skipping {name.upper()} check for {domain}: DNS resolution failed.")
            by_name[name] = _unresolved_result(domain, name)

    return [by_name[name] for name in MONITOR_ORDER if name in by_name]


async def scan_all(domains: list, monitors: dict, config: dict,
                   concurrency: int = DEFAULT_CONCURRENCY) -> list:
    """
    Scan every domain concurrently and return the results in config order.
    """
    sem = asyncio.Semaphore(max(1, concurrency))
    logger.info(f"Starting check for {len(domains)} domains (concurrency {concurrency})...")

    per_domain = await asyncio.gather(
        *(scan_domain(d, monitors, config, sem) for d in domains),
        return_exceptions=True,
    )

    results = []
    for raw_domain, output in zip(domains, per_domain, strict=True):
        if isinstance(output, Exception):
            logger.error(f"Scan failed for {raw_domain}: {output}")
            continue
        results.extend(output)
    return results
