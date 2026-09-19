import ipaddress

import dns.resolver
from loguru import logger

from src.constants import (
    DEFAULT_RBLS,
    MAX_IPS_PER_DOMAIN,
    RBL_BLOCKED_PREFIX,
    RBL_PBL_IPS,
)
from src.monitors.base_monitor import BaseMonitor


def rbl_query_name(ip: str) -> str:
    """
    Build the name a DNSBL is asked about.

    IPv4 reverses the octets (1.2.3.4 -> 4.3.2.1). IPv6 reverses the 32 hex
    nibbles, which is what the DNSBL specifications and PTR records under
    ip6.arpa both use.

    An IPv4-mapped address (::ffff:1.2.3.4) is that IPv4 address, and a DNSBL
    expects it in the IPv4 form, so it is unwrapped first. The nibbles come
    from the packed bytes rather than `.exploded`, whose IPv4-mapped rendering
    keeps a dotted quad on the end.
    """
    address = ipaddress.ip_address(ip)

    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped

    if address.version == 4:
        return ".".join(reversed(address.exploded.split(".")))
    return ".".join(reversed(address.packed.hex()))


class BlacklistMonitor(BaseMonitor):
    monitor_name = "blacklist"

    def __init__(self, rbls: list = None, **kwargs):
        super().__init__(**kwargs)
        # Override from config.yaml: monitors.blacklist.rbls
        self.rbls = list(rbls) if rbls else list(DEFAULT_RBLS)
        self.system_resolver = dns.resolver.Resolver()
        self.system_resolver.timeout = 2.0
        self.system_resolver.lifetime = 5.0

    @classmethod
    def from_config(cls, cfg: dict = None):
        return cls(rbls=(cfg or {}).get("rbls"))

    def check_blacklist(self, domain: str) -> dict:
        """Resolve the domain and check every address against the RBLs."""
        return self.check(domain)

    def _query_rbl(self, rbl: str, ip: str, domain: str) -> bool:
        """True when this RBL lists this address."""
        try:
            query = f"{rbl_query_name(ip)}.{rbl}"
        except ValueError:
            logger.warning(f"Skipping malformed address {ip!r} for {domain}")
            return False

        try:
            answers = self.system_resolver.resolve(query, "A")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return False  # not listed — the expected answer
        except Exception as e:
            logger.debug(f"{rbl} lookup failed for {ip}: {e}")
            return False

        for rdata in answers:
            code = rdata.to_text()

            # Query blocked / refused (e.g. 127.255.255.x via public DNS)
            if code.startswith(RBL_BLOCKED_PREFIX):
                logger.warning(
                    f"RBL {rbl} blocked query for {domain} (Code: {code}). Using public DNS?"
                )
                continue

            # PBL / Policy listings — dynamic/consumer IPs, not actionable
            if code in RBL_PBL_IPS:
                continue

            return True
        return False

    def _addresses(self, domain: str) -> list:
        """
        Every address the domain answers with, v4 and v6, capped.

        Resolving only the first A record left a CDN-hosted name mostly
        unchecked and an IPv6-only name failing outright.
        """
        from src.utils.dns_helpers import RobustResolver
        resolver = RobustResolver(timeout=2.0)

        addresses = resolver.get_ips(domain, "A") + resolver.get_ips(domain, "AAAA")

        # Preserve order while dropping duplicates
        unique = list(dict.fromkeys(addresses))
        if len(unique) > MAX_IPS_PER_DOMAIN:
            logger.info(
                f"{domain} resolves to {len(unique)} addresses; "
                f"checking the first {MAX_IPS_PER_DOMAIN}"
            )
        return unique[:MAX_IPS_PER_DOMAIN]

    def _run_check(self, domain: str) -> dict:
        addresses = self._addresses(domain)
        if not addresses:
            return self._error_result("Could not resolve domain")

        # rbl -> the addresses it lists
        listings = {}
        for ip in addresses:
            for rbl in self.rbls:
                if self._query_rbl(rbl, ip, domain):
                    listings.setdefault(rbl, []).append(ip)

        listed_in = list(listings)
        listed_ips = sorted({ip for ips in listings.values() for ip in ips})

        if listed_in:
            message = (
                f"Listed in {len(listed_in)} RBL(s)"
                if len(addresses) == 1
                else f"Listed in {len(listed_in)} RBL(s) "
                     f"for {len(listed_ips)} of {len(addresses)} addresses"
            )
        else:
            message = "Not listed in any common RBL"

        return {
            "monitor": self.monitor_name,
            "status": "critical" if listed_in else "ok",
            # `ip` stays for the report and for anything already reading it
            "ip": addresses[0],
            "ips": addresses,
            "listed_in": listed_in,
            "listed_ips": listed_ips,
            "listings": listings,
            "checked_rbls": len(self.rbls),
            "message": message,
        }
