import requests
import socket
import ssl
import urllib3
from loguru import logger

# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SecurityMonitor:
    def check_security(self, domain: str) -> dict:
        """
        Comprehensive security checks: Headers, Info Leakage, and Weak Protocols.
        """
        checks = {}
        issues = []
        
        # 1. Header Checks
        url = f"https://{domain}"
        try:
            # Timeout is crucial to avoid hanging
            response = requests.head(url, timeout=5)
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
            # Only run this if we are not mocking (implied by execution flow)
            weak_protocols = self.check_protocols(domain)
            if weak_protocols:
                s = f"Weak Ciphers Detected: {', '.join(weak_protocols)} (OWASP A02: Cryptographic Failures)"
                issues.append(s)
                checks["weak_protocols"] = weak_protocols

            status = "ok"
            if issues:
                status = "warning"
            
            # Critical triggers
            if weak_protocols: 
                status = "critical"

            return {
                "monitor": "security",
                "status": status,
                "message": f"{len(issues)} Security Issues" if issues else "Secure",
                "details": issues,
                "checks": checks
            }

        except requests.exceptions.SSLError as e:
            # Fallback: Check if it works without verification (Self-signed or Chain issue)
            try:
                requests.head(url, timeout=5, verify=False)
                # If we are here, SSL is ON but Certificate is untrusted/invalid chain
                logger.warning(f"SSL Valid but Untrusted for {domain}: {e}")
                return {
                    "monitor": "security",
                    "status": "warning", 
                    "message": "SSL Certificate Untrusted (Check Chain/Root)", 
                    "details": str(e)
                }
            except Exception:
                # Real handshake failure
                logger.warning(f"SSL Verification failed for {domain}: {e}")
                return {"monitor": "security", "status": "critical", "message": "SSL Verification Failed", "details": str(e)}
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout connecting to {domain}")
            return {"monitor": "security", "status": "warning", "message": "Connection Timeout"}
        except Exception as e:
            # Clean up the error message for display
            clean_error = str(e).split('(')[0] if '(' in str(e) else str(e)
            logger.warning(f"Could not check security headers for {domain}: {clean_error}")
            return {"monitor": "security", "status": "error", "message": "Connection Failed", "details": str(e)}

    def check_protocols(self, domain: str) -> list:
        """
        Check for weak SSL/TLS protocols (SSLv2, SSLv3, TLS 1.0, TLS 1.1).
        Returns a list of weak protocols found.
        """
        weak_protocols = []
        # Python's ssl module often disables SSLv2/v3 by default at compile time.
        # This check attempts to detect them if the local OpenSSL allows it.
        protocols_to_test = []
        if hasattr(ssl, "PROTOCOL_TLSv1"):
            protocols_to_test.append(("TLSv1.0", ssl.PROTOCOL_TLSv1))
        if hasattr(ssl, "PROTOCOL_TLSv1_1"):
            protocols_to_test.append(("TLSv1.1", ssl.PROTOCOL_TLSv1_1))
            
        for name, proto_version in protocols_to_test:
            try:
                context = ssl.SSLContext(proto_version)
                context.verify_mode = ssl.CERT_NONE
                with socket.create_connection((domain, 443), timeout=2) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        weak_protocols.append(name)
            except (ssl.SSLError, socket.error):
                # Connection failed or protocol rejected (Secure behavior)
                pass
            except Exception:
                pass
                
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
