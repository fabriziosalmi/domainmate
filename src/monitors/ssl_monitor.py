import ssl
import socket
from datetime import datetime, timezone
from loguru import logger

class SSLMonitor:
    def check_ssl(self, domain: str, port: int = 443) -> dict:
        """
        Check SSL certificate validity and expiration.
        """
        conn = None
        try:
            context = ssl.create_default_context()
            conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=domain)
            conn.settimeout(5.0)
            conn.connect((domain, port))
            cert = conn.getpeercert()

            not_after_str = cert['notAfter']
            # Format: 'Sep  8 12:00:00 2024 GMT'
            ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'
            expiration_date = datetime.strptime(not_after_str, ssl_date_fmt).replace(tzinfo=timezone.utc)

            days_until_expiry = (expiration_date - datetime.now(timezone.utc)).days

            status = "ok"
            if days_until_expiry < 30:
                status = "warning"
            if days_until_expiry < 7:
                status = "critical"

            issuer = dict(x[0] for x in cert['issuer'])
            common_name = issuer.get('commonName', 'Unknown')

            return {
                "monitor": "ssl",
                "status": status,
                "message": f"Expires in {days_until_expiry} days",
                "expiration_date": expiration_date.strftime("%Y-%m-%d"),
                "days_until_expiry": days_until_expiry,
                "issuer": common_name,
                "version": cert['version']
            }
        except Exception as e:
            logger.error(f"Error checking SSL for {domain}: {e}")
            return {"monitor": "ssl", "status": "error", "message": str(e)}
        finally:
            if conn is not None:
                conn.close()
