import dns.resolver
from loguru import logger

class DNSMonitor:
    def check_dns(self, domain: str) -> dict:
        """
        Check DNS records for SPF, DMARC.
        """
        results = {
            "monitor": "dns",
            "spf": {"status": "missing", "record": None},
            "dmarc": {"status": "missing", "record": None},
            "txt": []
        }

        try:
            # SPF Check
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')
                for r in txt_records:
                    txt_val = r.to_text().strip('"')
                    results["txt"].append(txt_val)
                    if txt_val.startswith("v=spf1"):
                        results["spf"] = {"status": "present", "record": txt_val}
            except Exception:
                pass

            # DMARC Check (_dmarc.domain)
            try:
                dmarc_records = dns.resolver.resolve(f"_dmarc.{domain}", 'TXT')
                for r in dmarc_records:
                    txt_val = r.to_text().strip('"')
                    if txt_val.startswith("v=DMARC1"):
                        results["dmarc"] = {"status": "present", "record": txt_val}
            except Exception:
                pass

            # Logic for overall status
            # If SPF or DMARC missing -> Warning
            status = "ok"
            if results["spf"]["status"] == "missing" or results["dmarc"]["status"] == "missing":
                status = "warning"
            
            results["status"] = status
            return results

        except Exception as e:
            logger.error(f"Error checking DNS for {domain}: {e}")
            return {"monitor": "dns", "status": "error", "message": str(e)}
