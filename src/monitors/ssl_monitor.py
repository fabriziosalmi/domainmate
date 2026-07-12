import ssl
import socket
from datetime import datetime, timezone
from loguru import logger
from src.monitors.base_monitor import BaseMonitor


class SSLMonitor(BaseMonitor):
    monitor_name = "ssl"

    def check_ssl(self, domain: str, port: int = 443) -> dict:
        """Check SSL certificate validity and expiration."""
        return self.check(domain)

    def _run_check(self, domain: str, port: int = 443) -> dict:
        conn = None
        try:
            context = ssl.create_default_context()
            raw_sock = socket.create_connection((domain, port), timeout=5.0)
            conn = context.wrap_socket(raw_sock, server_hostname=domain)
            cert = conn.getpeercert()
        finally:
            if conn is not None:
                conn.close()

        not_after_str = cert.get("notAfter")
        if not not_after_str:
            return self._error_result("Certificate missing notAfter field")

        ssl_date_fmt = r"%b %d %H:%M:%S %Y %Z"
        expiration_date = datetime.strptime(not_after_str, ssl_date_fmt).replace(
            tzinfo=timezone.utc
        )

        days_until_expiry = (expiration_date - datetime.now(timezone.utc)).days
        status = self.get_expiry_status(days_until_expiry)

        # Safely parse issuer
        try:
            issuer = dict(x[0] for x in cert.get("issuer", []))
            common_name = issuer.get("commonName", "Unknown")
        except Exception:
            logger.warning(f"Could not parse issuer for {domain}")
            common_name = "Unknown"

        return {
            "monitor": self.monitor_name,
            "status": status,
            "message": f"Expires in {days_until_expiry} days",
            "expiration_date": expiration_date.strftime("%Y-%m-%d"),
            "days_until_expiry": days_until_expiry,
            "issuer": common_name,
            "version": cert.get("version"),
        }
