import whois
from datetime import datetime
from loguru import logger

class DomainMonitor:
    def check_domain(self, domain: str) -> dict:
        """
        Check domain expiration and status using WHOIS.
        """
        try:
            w = whois.whois(domain)
            
            # Handle list of dates (some registrars return list)
            expiration_date = w.expiration_date
            if isinstance(expiration_date, list):
                expiration_date = expiration_date[0]
            
            if not expiration_date:
                return {"status": "error", "message": "Could not retrieve expiration date"}

            # Handle Timedeltas with potentially timezone-aware datetimes
            now = datetime.now()
            if expiration_date.tzinfo:
                now = now.replace(tzinfo=expiration_date.tzinfo)
            
            days_until_expiry = (expiration_date - now).days
            
            status = "ok"
            if days_until_expiry < 30:
                status = "warning"
            if days_until_expiry < 7:
                status = "critical"

            return {
                "monitor": "domain",
                "status": status,
                "expiration_date": expiration_date.strftime("%Y-%m-%d"),
                "days_until_expiry": days_until_expiry,
                "registrar": w.registrar,
                "details": w
            }
        except Exception as e:
            logger.error(f"Error checking domain {domain}: {e}")
            return {"monitor": "domain", "status": "error", "message": str(e)}
