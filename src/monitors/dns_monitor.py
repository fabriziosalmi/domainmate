import dns.resolver
from loguru import logger

from src.constants import (
    DEFAULT_REQUIRED_RECORDS,
    STATUS_OK,
    STATUS_WARNING,
    SUPPORTED_REQUIRED_RECORDS,
)
from src.monitors.base_monitor import BaseMonitor


class DNSMonitor(BaseMonitor):
    monitor_name = "dns"

    def __init__(self, required_records: list = None, **kwargs):
        super().__init__(**kwargs)
        # Override from config.yaml: monitors.dns.required_records
        requested = required_records if required_records else DEFAULT_REQUIRED_RECORDS
        self.required_records = []
        for record in requested:
            name = str(record).strip().lower()
            if name in SUPPORTED_REQUIRED_RECORDS:
                if name not in self.required_records:
                    self.required_records.append(name)
            else:
                logger.warning(
                    f"monitors.dns.required_records: '{record}' is not a record "
                    f"this monitor can check (supported: "
                    f"{', '.join(sorted(SUPPORTED_REQUIRED_RECORDS))}); skipping it"
                )

    @classmethod
    def from_config(cls, cfg: dict = None):
        return cls(required_records=(cfg or {}).get("required_records"))

    def check_dns(self, domain: str) -> dict:
        """Check DNS records for the configured record types."""
        return self.check(domain)

    # ── Per-record checks ─────────────────────────────────────────────────────

    def _txt_values(self, qname: str) -> list:
        """Resolve TXT and join each record's character-strings."""
        answers = dns.resolver.resolve(qname, "TXT")
        return [b"".join(r.strings).decode("utf-8", errors="replace") for r in answers]

    def _check_prefixed_txt(self, qname: str, prefix: str) -> dict:
        """Look for a TXT record starting with `prefix` (SPF, DMARC)."""
        try:
            for value in self._txt_values(qname):
                if value.startswith(prefix):
                    return {"status": "present", "record": value}
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        except Exception as e:
            logger.warning(f"{prefix} lookup failed for {qname}: {e}")
        return {"status": "missing", "record": None}

    def _check_present(self, qname: str, rdtype: str) -> dict:
        """Look for any record of a type (MX, CAA)."""
        try:
            answers = dns.resolver.resolve(qname, rdtype)
            records = [r.to_text() for r in answers]
            if records:
                return {"status": "present", "record": records[0], "records": records}
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        except Exception as e:
            logger.warning(f"{rdtype} lookup failed for {qname}: {e}")
        return {"status": "missing", "record": None}

    def _run_check(self, domain: str) -> dict:
        results: dict = {"monitor": self.monitor_name, "txt": []}

        # TXT is fetched once: SPF lives there, and the full list is reported.
        txt_values = []
        try:
            txt_values = self._txt_values(domain)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass
        except Exception as e:
            logger.warning(f"TXT lookup failed for {domain}: {e}")
        results["txt"] = txt_values

        for record in self.required_records:
            if record == "spf":
                found = next((v for v in txt_values if v.startswith("v=spf1")), None)
                results["spf"] = ({"status": "present", "record": found} if found
                                  else {"status": "missing", "record": None})
            elif record == "dmarc":
                results["dmarc"] = self._check_prefixed_txt(f"_dmarc.{domain}", "v=DMARC1")
            elif record == "mx":
                results["mx"] = self._check_present(domain, "MX")
            elif record == "caa":
                results["caa"] = self._check_present(domain, "CAA")

        missing = [r for r in self.required_records if results[r]["status"] == "missing"]
        present = [r for r in self.required_records if results[r]["status"] == "present"]

        results["required_records"] = list(self.required_records)
        results["status"] = STATUS_WARNING if missing else STATUS_OK
        results["message"] = (
            f"Missing: {', '.join(m.upper() for m in missing)}"
            if missing
            else f"{' and '.join(p.upper() for p in present)} present"
            if present
            else "No records required"
        )
        return results
