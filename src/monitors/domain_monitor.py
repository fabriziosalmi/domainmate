import whois
from datetime import datetime, timezone
from loguru import logger

from src.monitors import rdap
from src.monitors.base_monitor import BaseMonitor


class DomainMonitor(BaseMonitor):
    monitor_name = "domain"

    def __init__(self, use_rdap: bool = True, **kwargs):
        super().__init__(**kwargs)
        # Override from config.yaml: monitors.domain.use_rdap
        self.use_rdap = use_rdap

    @classmethod
    def from_config(cls, cfg: dict = None):
        cfg = cfg or {}
        base = super().from_config(cfg)
        base.use_rdap = bool(cfg.get("use_rdap", True))
        return base

    def check_domain(self, domain: str) -> dict:
        """Check domain expiration and status, preferring RDAP over WHOIS."""
        return self.check(domain)

    # ── Lookup strategies ─────────────────────────────────────────────────────

    def _lookup_whois(self, domain: str) -> dict:
        w = whois.whois(domain)

        # Some registrars return a list of dates
        expiration_date = w.expiration_date
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0] if expiration_date else None

        if not expiration_date:
            raise ValueError("WHOIS carried no expiration date")

        # Normalise to UTC so comparison is always timezone-aware
        if expiration_date.tzinfo is None:
            expiration_date = expiration_date.replace(tzinfo=timezone.utc)

        return {"expiration_date": expiration_date, "registrar": w.registrar}

    def _lookup(self, domain: str) -> tuple:
        """
        Return (data, source). RDAP first: it speaks HTTPS on 443 rather than
        WHOIS on 43, which is blocked in most containers and CI runners, and it
        answers with structured JSON instead of text that needs parsing.
        WHOIS remains the fallback for TLDs with no RDAP server.
        """
        if self.use_rdap:
            try:
                return self._lookup_rdap(domain), "rdap"
            except rdap.RDAPError as e:
                logger.info(f"RDAP unavailable for {domain} ({e}); falling back to WHOIS")

        return self._lookup_whois(domain), "whois"

    def _lookup_rdap(self, domain: str) -> dict:
        return rdap.lookup(domain)

    # ── Check ─────────────────────────────────────────────────────────────────

    def _run_check(self, domain: str) -> dict:
        try:
            data, source = self._lookup(domain)
        except Exception as e:
            logger.warning(f"Domain lookup failed for {domain}: {e}")
            return self._error_result("Could not retrieve expiration date")

        expiration_date = data["expiration_date"]
        days_until_expiry = (expiration_date - datetime.now(timezone.utc)).days
        status = self.get_expiry_status(days_until_expiry)

        return {
            "monitor": self.monitor_name,
            "status": status,
            "message": f"Expires in {days_until_expiry} days",
            "expiration_date": expiration_date.strftime("%Y-%m-%d"),
            "days_until_expiry": days_until_expiry,
            "registrar": data.get("registrar"),
            "source": source,
        }
