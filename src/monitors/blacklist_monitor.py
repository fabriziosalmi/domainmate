import dns.resolver
import socket
from loguru import logger
from src.monitors.base_monitor import BaseMonitor
from src.constants import DEFAULT_RBLS, RBL_BLOCKED_PREFIX, RBL_PBL_IPS


class BlacklistMonitor(BaseMonitor):
    monitor_name = "blacklist"

    def __init__(self, rbls: list = None):
        # Allow override from config; fall back to shared constant
        self.rbls = rbls if rbls is not None else list(DEFAULT_RBLS)
        self.system_resolver = dns.resolver.Resolver()
        self.system_resolver.timeout = 2.0
        self.system_resolver.lifetime = 5.0

    def check_blacklist(self, domain: str) -> dict:
        """Resolve domain to IP and check against common RBLs."""
        return self.check(domain)

    def _run_check(self, domain: str) -> dict:
        from src.utils.dns_helpers import RobustResolver
        resolver = RobustResolver(timeout=2.0)

        # 1. Resolve Domain to IP
        try:
            ip = resolver.get_ip(domain)
        except Exception as e:
            return self._error_result(f"Could not resolve domain: {e}")

        # 2. Prepare Reverse IP for DNSBL query (1.2.3.4 -> 4.3.2.1)
        reversed_ip = ".".join(reversed(ip.split(".")))

        listed_in = []
        errors = []

        # 3. Query RBLs
        for rbl in self.rbls:
            query = f"{reversed_ip}.{rbl}"
            try:
                answers = self.system_resolver.resolve(query, "A")
                for rdata in answers:
                    result_ip = rdata.to_text()

                    # Query blocked / refused (e.g. 127.255.255.x via public DNS)
                    if result_ip.startswith(RBL_BLOCKED_PREFIX):
                        logger.warning(
                            f"RBL {rbl} blocked query for {domain} (Code: {result_ip}). Using public DNS?"
                        )
                        continue

                    # PBL / Policy listings — dynamic/consumer IPs, not actionable
                    if result_ip in RBL_PBL_IPS:
                        continue

                    if rbl not in listed_in:
                        listed_in.append(rbl)

            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                # Not listed — expected result
                pass
            except Exception as e:
                errors.append(f"{rbl}: {e}")

        status = "critical" if listed_in else "ok"
        return {
            "monitor": self.monitor_name,
            "status": status,
            "ip": ip,
            "listed_in": listed_in,
            "checked_rbls": len(self.rbls),
            "message": (
                f"Listed in {len(listed_in)} blacklists"
                if listed_in
                else "Not listed in any common RBL"
            ),
        }
