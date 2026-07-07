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
                    # Join character-string fragments: long TXT records are split into 255-byte chunks
                    txt_val = b"".join(r.strings).decode("utf-8", errors="replace")
                    results["txt"].append(txt_val)
                    if txt_val.startswith("v=spf1"):
                        results["spf"] = {"status": "present", "record": txt_val}
            except Exception:
                pass

            # DMARC Check (_dmarc.domain)
            try:
                dmarc_records = dns.resolver.resolve(f"_dmarc.{domain}", 'TXT')
                for r in dmarc_records:
                    txt_val = b"".join(r.strings).decode("utf-8", errors="replace")
                    if txt_val.startswith("v=DMARC1"):
                        results["dmarc"] = {"status": "present", "record": txt_val}
            except Exception:
                pass

            missing = [k for k in ("spf", "dmarc") if results[k]["status"] == "missing"]
            results["status"] = "warning" if missing else "ok"
            results["message"] = (
                f"Missing: {', '.join(m.upper() for m in missing)}" if missing
                else "SPF and DMARC present"
            )
            return results

        except Exception as e:
            logger.error(f"Error checking DNS for {domain}: {e}")
            return {"monitor": "dns", "status": "error", "message": str(e)}
