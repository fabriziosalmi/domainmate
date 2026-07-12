import dns.resolver
from loguru import logger
from src.monitors.base_monitor import BaseMonitor


class DNSMonitor(BaseMonitor):
    monitor_name = "dns"

    def check_dns(self, domain: str) -> dict:
        """Check DNS records for SPF, DMARC."""
        return self.check(domain)

    def _run_check(self, domain: str) -> dict:
        results: dict = {
            "monitor": self.monitor_name,
            "spf": {"status": "missing", "record": None},
            "dmarc": {"status": "missing", "record": None},
            "txt": [],
        }

        # SPF Check
        try:
            txt_records = dns.resolver.resolve(domain, "TXT")
            for r in txt_records:
                txt_val = b"".join(r.strings).decode("utf-8", errors="replace")
                results["txt"].append(txt_val)
                if txt_val.startswith("v=spf1"):
                    results["spf"] = {"status": "present", "record": txt_val}
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        except Exception as e:
            logger.warning(f"TXT/SPF lookup failed for {domain}: {e}")

        # DMARC Check (_dmarc.domain)
        try:
            dmarc_records = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            for r in dmarc_records:
                txt_val = b"".join(r.strings).decode("utf-8", errors="replace")
                if txt_val.startswith("v=DMARC1"):
                    results["dmarc"] = {"status": "present", "record": txt_val}
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        except Exception as e:
            logger.warning(f"DMARC lookup failed for {domain}: {e}")

        missing = [k for k in ("spf", "dmarc") if results[k]["status"] == "missing"]
        results["status"] = "warning" if missing else "ok"
        results["message"] = (
            f"Missing: {', '.join(m.upper() for m in missing)}"
            if missing
            else "SPF and DMARC present"
        )
        return results
