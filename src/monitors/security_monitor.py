import requests
import socket
import ssl
from loguru import logger
from src.monitors.base_monitor import BaseMonitor
from src.constants import TIMEOUT_SOCKET, TIMEOUT_WEAK_PROTO


class SecurityMonitor(BaseMonitor):
    monitor_name = "security"

    def check_security(self, domain: str) -> dict:
        """Comprehensive security checks: Headers, Info Leakage, and Weak Protocols."""
        return self.check(domain)

    def _run_check(self, domain: str) -> dict:
        checks = {}
        issues = []

        # 1. Header Checks
        url = f"https://{domain}"
        try:
            # allow_redirects: without it headers are read from the 3xx response, not the final page
            response = requests.head(url, timeout=TIMEOUT_SOCKET, allow_redirects=True)
            headers = response.headers

            security_headers = {
                "HSTS": headers.get("Strict-Transport-Security"),
                "X-Frame-Options": headers.get("X-Frame-Options"),
                "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
                "Content-Security-Policy": headers.get("Content-Security-Policy"),
            }

            checks["headers"] = security_headers

            if not security_headers["HSTS"]:
                issues.append("Missing HSTS (OWASP A05)")
            if not security_headers["Content-Security-Policy"]:
                issues.append("Missing CSP (OWASP A05 - XSS Risk)")

            # 2. Info Leakage
            leaks = self.check_info_leakage(headers)
            if leaks:
                issues.extend(leaks)
                checks["info_leakage"] = leaks

            # 3. Protocol Check
            weak_protocols = self.check_protocols(domain)
            if weak_protocols:
                s = f"Weak Ciphers Detected: {', '.join(weak_protocols)} (OWASP A02: Cryptographic Failures)"
                issues.append(s)
                checks["weak_protocols"] = weak_protocols

            from src.constants import STATUS_OK, STATUS_WARNING, STATUS_CRITICAL
            if weak_protocols:
                status_val = STATUS_CRITICAL
            elif issues:
                status_val = STATUS_WARNING
            else:
                status_val = STATUS_OK

            return {
                "monitor": self.monitor_name,
                "status": status_val,
                "message": f"{len(issues)} Security Issues" if issues else "Secure",
                "details": issues,
                "checks": checks,
            }

        except requests.exceptions.SSLError as e:
            # Fallback: SSL verification failed — do NOT retry with verify=False
            logger.warning(f"SSL Verification failed for {domain}: {e}")
            return self._critical_result("SSL Verification Failed")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout connecting to {domain}")
            return self._warning_result("Connection Timeout")
        except Exception as e:
            clean_error = str(e).split("(")[0] if "(" in str(e) else str(e)
            logger.warning(f"Could not check security headers for {domain}: {clean_error}")
            return self._error_result("Connection Failed")

    def check_protocols(self, domain: str) -> list:
        """
        Check for weak SSL/TLS protocols (TLS 1.0, TLS 1.1).
        Returns a list of weak protocol names found.

        Note: ssl.CERT_NONE is intentional here — we are probing whether the
        *remote server* accepts deprecated protocol versions, not validating
        its certificate.
        """
        weak_protocols = []
        protocols_to_test = []
        if hasattr(ssl, "PROTOCOL_TLSv1"):
            protocols_to_test.append(("TLSv1.0", ssl.PROTOCOL_TLSv1))  # noqa: E501 # type: ignore[attr-defined]
        if hasattr(ssl, "PROTOCOL_TLSv1_1"):
            protocols_to_test.append(("TLSv1.1", ssl.PROTOCOL_TLSv1_1))  # noqa: E501 # type: ignore[attr-defined]

        for name, proto_version in protocols_to_test:
            try:
                context = ssl.SSLContext(proto_version)
                context.verify_mode = ssl.CERT_NONE  # intentional: testing remote protocol support
                with socket.create_connection((domain, 443), timeout=TIMEOUT_WEAK_PROTO) as sock:
                    with context.wrap_socket(sock, server_hostname=domain):
                        weak_protocols.append(name)
            except (ssl.SSLError, OSError):
                # Connection refused or protocol rejected — secure behaviour
                pass
            except Exception as e:
                logger.debug(f"Weak-protocol probe for {domain} ({name}) raised unexpected error: {e}")

        return weak_protocols

    def check_info_leakage(self, headers: dict) -> list:
        """
        Check for info leakage in headers (Server, X-Powered-By).
        OWASP A05:2021 - Security Misconfiguration.
        """
        leaks = []
        if "Server" in headers:
            leaks.append(f"Server Version Disclosed: {headers['Server']}")
        if "X-Powered-By" in headers:
            leaks.append(f"Tech Stack Disclosed: {headers['X-Powered-By']}")
        if "X-AspNet-Version" in headers:
            leaks.append(f"ASP.NET Version Disclosed: {headers['X-AspNet-Version']}")
        return leaks
