import whois
from datetime import datetime, timezone
from src.monitors.base_monitor import BaseMonitor


class DomainMonitor(BaseMonitor):
    monitor_name = "domain"

    def check_domain(self, domain: str) -> dict:
        """Check domain expiration and status using WHOIS."""
        return self.check(domain)

    def _run_check(self, domain: str) -> dict:
        w = whois.whois(domain)

        # Handle list of dates (some registrars return a list)
        expiration_date = w.expiration_date
        if isinstance(expiration_date, list):
            # Guard against empty list
            expiration_date = expiration_date[0] if expiration_date else None

        if not expiration_date:
            return self._error_result("Could not retrieve expiration date")

        # Normalise to UTC so comparison is always timezone-aware
        if expiration_date.tzinfo is None:
            expiration_date = expiration_date.replace(tzinfo=timezone.utc)

        days_until_expiry = (expiration_date - datetime.now(timezone.utc)).days
        status = self.get_expiry_status(days_until_expiry)

        return {
            "monitor": self.monitor_name,
            "status": status,
            "message": f"Expires in {days_until_expiry} days",
            "expiration_date": expiration_date.strftime("%Y-%m-%d"),
            "days_until_expiry": days_until_expiry,
            "registrar": w.registrar,
        }
