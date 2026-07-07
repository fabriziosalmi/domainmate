from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from src.monitors.domain_monitor import DomainMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.security_monitor import SecurityMonitor


def _whois_result(days_from_now, as_list=False):
    exp = datetime.now() + timedelta(days=days_from_now)
    return SimpleNamespace(
        expiration_date=[exp] if as_list else exp,
        registrar="Test Registrar",
    )


class TestDomainMonitor:
    def test_ok_status(self):
        with patch("src.monitors.domain_monitor.whois.whois", return_value=_whois_result(100)):
            res = DomainMonitor().check_domain("example.com")
        assert res["status"] == "ok"
        assert res["monitor"] == "domain"
        assert res["registrar"] == "Test Registrar"

    def test_warning_under_30_days(self):
        with patch("src.monitors.domain_monitor.whois.whois", return_value=_whois_result(15)):
            assert DomainMonitor().check_domain("example.com")["status"] == "warning"

    def test_critical_under_7_days(self):
        with patch("src.monitors.domain_monitor.whois.whois", return_value=_whois_result(3)):
            assert DomainMonitor().check_domain("example.com")["status"] == "critical"

    def test_expiration_date_list_handled(self):
        with patch("src.monitors.domain_monitor.whois.whois", return_value=_whois_result(100, as_list=True)):
            assert DomainMonitor().check_domain("example.com")["status"] == "ok"

    def test_missing_expiration_is_error_with_monitor_key(self):
        w = SimpleNamespace(expiration_date=None, registrar=None)
        with patch("src.monitors.domain_monitor.whois.whois", return_value=w):
            res = DomainMonitor().check_domain("example.com")
        assert res["status"] == "error"
        assert res["monitor"] == "domain"


class _FakeTXT:
    def __init__(self, *chunks):
        self.strings = tuple(c.encode() for c in chunks)


def _fake_resolve(spf_chunks=None, dmarc=None):
    def resolve(qname, rdtype):
        if str(qname).startswith("_dmarc."):
            if dmarc is None:
                raise Exception("NXDOMAIN")
            return [_FakeTXT(dmarc)]
        records = [_FakeTXT("some-verification=abc")]
        if spf_chunks is not None:
            records.append(_FakeTXT(*spf_chunks))
        return records
    return resolve


class TestDNSMonitor:
    def test_spf_and_dmarc_present(self):
        fake = _fake_resolve(spf_chunks=["v=spf1 include:_spf.google.com ~all"], dmarc="v=DMARC1; p=reject;")
        with patch("src.monitors.dns_monitor.dns.resolver.resolve", side_effect=fake):
            res = DNSMonitor().check_dns("example.com")
        assert res["status"] == "ok"
        assert res["message"] == "SPF and DMARC present"
        assert res["spf"]["status"] == "present"
        assert res["dmarc"]["status"] == "present"

    def test_multistring_spf_joined(self):
        # Long SPF records are split into 255-byte character-strings; they must be joined
        fake = _fake_resolve(spf_chunks=["v=spf1 include:a.example.com ", "include:b.example.com ~all"])
        with patch("src.monitors.dns_monitor.dns.resolver.resolve", side_effect=fake):
            res = DNSMonitor().check_dns("example.com")
        assert res["spf"]["status"] == "present"
        assert res["spf"]["record"] == "v=spf1 include:a.example.com include:b.example.com ~all"

    def test_missing_dmarc_is_warning(self):
        fake = _fake_resolve(spf_chunks=["v=spf1 ~all"], dmarc=None)
        with patch("src.monitors.dns_monitor.dns.resolver.resolve", side_effect=fake):
            res = DNSMonitor().check_dns("example.com")
        assert res["status"] == "warning"
        assert "DMARC" in res["message"]


class TestSecurityMonitor:
    def test_info_leakage_detected(self):
        leaks = SecurityMonitor().check_info_leakage({"Server": "nginx/1.25", "X-Powered-By": "PHP/8.2"})
        assert len(leaks) == 2

    def test_no_leakage_on_clean_headers(self):
        assert SecurityMonitor().check_info_leakage({"Content-Type": "text/html"}) == []
