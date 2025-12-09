import dns.resolver
import requests
from loguru import logger
import random
import time

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

        last_exception = None

        # Strategy: Try chunks of resolvers or just iterate? 
        # Iterating through ALL might be slow if timeout is high. 
        # Let's try up to 3 different sets of nameservers.
        
        # We can just set the nameservers to our full list? 
        # Standard dns.resolver uses the list in order/round-robin. 
        # But if we want *specific* fallback explicitly (e.g. if Google fails, try Cloudflare),
        # we can just populate the default resolver with our robust list.
        
        resolver.nameservers = current_resolvers

        try:
             # This will use the configured nameservers with the built-in logic of dnspython
             return resolver.resolve(qname, rdtype)
        except Exception as e:
            # If the "batch" failed, maybe valid NXDOMAIN or NoAnswer?
            # If NXDOMAIN, that's authoritative (usually).
            if isinstance(e, (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer)):
                raise e
            
            # If Timeout, we might want to try one last desperate attempt with system default?
            # Or just raise. With 8+ resolvers, if all fail, it's likely down or network issue.
            # Fallback to DoH (DNS over HTTPS) - Firewall piercing
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
                    
                answers = []
                for ans in data["Answer"]:
                    if ans["type"] == 1: # A record
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
