import dns.resolver
import socket
from loguru import logger

class BlacklistMonitor:
    def __init__(self):
        # Common free RBLs (Real-time Blackhole Lists)
        self.rbls = [
            "zen.spamhaus.org",
            "bl.spamcop.net",
            "cbl.abuseat.org",
            "dnsbl.sorbs.net",
            "b.barracudacentral.org", # Often requires registration but worth a try
            "dnsbl-1.uceprotect.net"
        ]
        self.system_resolver = dns.resolver.Resolver()

    def check_blacklist(self, domain: str) -> dict:
        """
        Resolve domain to IP and check against common RBLs.
        """
        status = "ok"
        listed_in = []
        errors = []
        ip = None

        try:
            from src.utils.dns_helpers import RobustResolver
            resolver = RobustResolver(timeout=2.0)

            # 1. Resolve Domain to IP
            try:
                # Use robust resolver instead of socket.gethostbyname
                ip = resolver.get_ip(domain)
            except Exception as e:
                return {"monitor": "blacklist", "status": "error", "message": f"Could not resolve domain: {e}"}

            # 2. Prepare Reverse IP for DNSBL query (1.2.3.4 -> 4.3.2.1)
            reversed_ip = ".".join(reversed(ip.split(".")))

            # 3. Query RBLs
            for rbl in self.rbls:
                query = f"{reversed_ip}.{rbl}"
                try:
                    # Use System Resolver for RBLs (Often allows what Public DNS blocks)
                    answers = self.system_resolver.resolve(query, 'A')
                    for rdata in answers:
                        result_ip = rdata.to_text()
                        
                        # GLOBAL RBL FILTERS
                        
                        # 1. Query Refused / Blocked (e.g. 127.255.255.x for Spamhaus/CBL via Public DNS)
                        if result_ip.startswith("127.255.255."):
                             logger.warning(f"RBL {rbl} blocked query for {domain} (Code: {result_ip}). Using public DNS?")
                             continue

                        # 2. PBL / Policy Listings (127.0.0.10/11) - Often dynamic/consumer IPs
                        if result_ip in ["127.0.0.10", "127.0.0.11"]:
                            continue 
                        
                        # Valid Listing
                        if rbl not in listed_in:
                            listed_in.append(rbl)

                except dns.resolver.NXDOMAIN:
                    # Not listed
                    pass
                except dns.resolver.NoAnswer:
                    # Not listed
                    pass
                except Exception as e:
                    # Timeout or other error
                    errors.append(f"{rbl}: {e}")

            if listed_in:
                status = "critical" # Being blacklisted is usually critical for email deliverability
            
            return {
                "monitor": "blacklist",
                "status": status,
                "ip": ip,
                "listed_in": listed_in,
                "checked_rbls": len(self.rbls),
                "message": f"Listed in {len(listed_in)} blacklists" if listed_in else "Not listed in any common RBL"
            }

        except Exception as e:
            logger.error(f"Error checking blacklist for {domain}: {e}")
            return {"monitor": "blacklist", "status": "error", "message": str(e)}
