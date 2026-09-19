import random

import dns.rdatatype
import dns.resolver
import requests
from loguru import logger


class RobustResolver:
    """
    DNS Resolver with multiple provider fallback and retry logic.
    """
    def __init__(self, timeout: float = 2.0, total_timeout: float = 5.0):
        self.resolvers = [
            '1.1.1.1', '1.0.0.1',           # Cloudflare
            '8.8.8.8', '8.8.4.4',           # Google
            '9.9.9.9', '149.112.112.112',   # Quad9
            '208.67.222.222',               # OpenDNS
            '64.6.64.6'                     # Verisign
        ]
        self.timeout = timeout
        self.total_timeout = total_timeout

    def resolve(self, qname: str, rdtype: str = 'A') -> list:
        """
        Resolve a query attempting multiple resolvers if necessary.
        """
        # Shuffle resolvers to load balance and avoid hitting the same blocked one first every time
        current_resolvers = self.resolvers.copy()
        random.shuffle(current_resolvers)

        # Create a customized resolver instance
        resolver = dns.resolver.Resolver()
        resolver.timeout = self.timeout
        resolver.lifetime = self.total_timeout

        # dnspython rotates through the whole list itself, so handing it every
        # resolver at once is the fallback.
        resolver.nameservers = current_resolvers

        try:
            return resolver.resolve(qname, rdtype)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            # Authoritative answers: the name genuinely has no such record, and
            # asking over another transport would not change that.
            raise
        except Exception:
            # Every resolver failed to answer at all. That usually means UDP/53
            # is blocked rather than that the name is gone, so try DNS-over-HTTPS.
            return self._resolve_doh(qname, rdtype)

    def _resolve_doh(self, qname: str, rdtype: str) -> list:
        """
        Fallback to Cloudflare DNS-over-HTTPS.
        """
        try:
            # Cloudflare DoH API
            url = "https://cloudflare-dns.com/dns-query"
            params = {"name": qname, "type": rdtype}
            headers = {"Accept": "application/dns-json"}

            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if data.get("Status") == 0 and "Answer" in data:
                # Mock Rdata object to mimic dnspython response (or just return simpler list?)
                # For compatibility with BlacklistMonitor which expects rdata.to_text(),
                # we should construct a simple object or just return strings if we change the consumer.
                # To minimize consumer change, let's return a list of objects with a to_text() method.

                class DoHAnswer:
                    def __init__(self, val): self.val = val
                    def to_text(self): return self.val

                wanted_type = dns.rdatatype.from_text(rdtype)
                answers = []
                for ans in data["Answer"]:
                    if ans["type"] == wanted_type:
                        answers.append(DoHAnswer(ans["data"]))

                if answers:
                    return answers

            raise Exception(f"DoH Refused or No Data: {data.get('Status')}")

        except Exception as e:
            logger.warning(f"DoH resolution failed for {qname}: {e}")
            raise e

    def get_ip(self, domain: str) -> str:
        """
        Simple helper to get a single IP (replacement for socket.gethostbyname).
        """
        try:
            # Try 127.0.0.1 for localhost logic if needed, but assuming external scans
            answers = self.resolve(domain, 'A')
            for rdata in answers:
                return rdata.to_text()
            raise Exception("No A records found")
        except Exception as e:
            raise Exception(f"Failed to resolve IP for {domain}: {e}")
