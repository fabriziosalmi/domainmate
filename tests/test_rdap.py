"""
RDAP lookups and the WHOIS fallback.

The payloads below follow RFC 9083 and mirror what registry servers actually
return. Nothing here touches the network: every response is injected.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from src.monitors import rdap
from src.monitors.domain_monitor import DomainMonitor

# ── Fixtures shaped like real registry responses ─────────────────────────────

def _payload(expiry="2027-08-13T04:00:00Z", registrar="Example Registrar, Inc.",
             action="expiration"):
    body = {
        "objectClassName": "domain",
        "handle": "2336799_DOMAIN_COM-VRSN",
        "ldhName": "EXAMPLE.COM",
        "status": ["client delete prohibited"],
        "events": [
            {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
            {"eventAction": "last changed", "eventDate": "2025-08-14T07:01:34Z"},
        ],
    }
    if expiry:
        body["events"].append({"eventAction": action, "eventDate": expiry})
    if registrar:
        body["entities"] = [{
            "objectClassName": "entity",
            "handle": "292",
            "roles": ["registrar"],
            "vcardArray": ["vcard", [
                ["version", {}, "text", "4.0"],
                ["fn", {}, "text", registrar],
            ]],
        }]
    return body


class _Response:
    def __init__(self, payload, status_code=200, json_error=False):
        self._payload = payload
        self.status_code = status_code
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("Expecting value")
        return self._payload


def _get(payload=None, **kw):
    return patch("src.monitors.rdap.requests.get", return_value=_Response(payload, **kw))


# ── Parsing ──────────────────────────────────────────────────────────────────

def test_reads_expiration_and_registrar():
    with _get(_payload()):
        out = rdap.lookup("example.com")
    assert out["expiration_date"] == datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)
    assert out["registrar"] == "Example Registrar, Inc."


def test_uses_the_bootstrap_url():
    with _get(_payload()) as mock:
        rdap.lookup("example.com")
    url = mock.call_args[0][0]
    assert url == "https://rdap.org/domain/example.com"
    assert mock.call_args[1]["allow_redirects"] is True
    assert "application/rdap+json" in mock.call_args[1]["headers"]["Accept"]


@pytest.mark.parametrize("raw,expected", [
    ("2027-08-13T04:00:00Z", datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)),
    ("2027-08-13T04:00:00z", datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)),
    ("2027-08-13T04:00:00+00:00", datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)),
    ("2027-08-13T06:00:00+02:00", datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)),
    ("2027-08-13T04:00:00.123Z", datetime(2027, 8, 13, 4, 0, 0, 123000, tzinfo=timezone.utc)),
    ("2027-08-13T04:00:00", datetime(2027, 8, 13, 4, 0, tzinfo=timezone.utc)),
])
def test_event_date_formats(raw, expected):
    with _get(_payload(expiry=raw)):
        assert rdap.lookup("example.com")["expiration_date"] == expected


def test_older_expiry_spelling_accepted():
    with _get(_payload(action="expiry")):
        assert rdap.lookup("example.com")["expiration_date"].year == 2027


def test_registrar_falls_back_to_handle_without_a_jcard():
    body = _payload(registrar=None)
    body["entities"] = [{"roles": ["registrar"], "handle": "REG-292"}]
    with _get(body):
        assert rdap.lookup("example.com")["registrar"] == "REG-292"


def test_registrar_is_optional():
    with _get(_payload(registrar=None)):
        assert rdap.lookup("example.com")["registrar"] is None


def test_non_registrar_entities_are_ignored():
    body = _payload(registrar="The Registrar")
    body["entities"].insert(0, {
        "roles": ["technical"],
        "vcardArray": ["vcard", [["fn", {}, "text", "Some Tech Contact"]]],
    })
    with _get(body):
        assert rdap.lookup("example.com")["registrar"] == "The Registrar"


# ── Everything that must send the caller to WHOIS ────────────────────────────

def test_404_means_no_rdap_record():
    with _get(None, status_code=404):
        with pytest.raises(rdap.RDAPError, match="no RDAP record"):
            rdap.lookup("example.com")


def test_server_error_is_reported():
    with _get(None, status_code=503):
        with pytest.raises(rdap.RDAPError, match="HTTP 503"):
            rdap.lookup("example.com")


def test_transport_failure_is_wrapped():
    with patch("src.monitors.rdap.requests.get",
               side_effect=requests.Timeout("timed out")):
        with pytest.raises(rdap.RDAPError, match="request failed"):
            rdap.lookup("example.com")


def test_non_json_response_is_wrapped():
    with _get(None, json_error=True):
        with pytest.raises(rdap.RDAPError, match="not JSON"):
            rdap.lookup("example.com")


def test_payload_without_expiration_is_rejected():
    with _get(_payload(expiry=None)):
        with pytest.raises(rdap.RDAPError, match="no expiration event"):
            rdap.lookup("example.com")


def test_unparseable_event_date_is_rejected():
    with _get(_payload(expiry="not-a-date")):
        with pytest.raises(rdap.RDAPError, match="no expiration event"):
            rdap.lookup("example.com")


def test_response_that_is_not_an_object_is_rejected():
    with _get(["not", "an", "object"]):
        with pytest.raises(rdap.RDAPError, match="not an RDAP object"):
            rdap.lookup("example.com")


# ── DomainMonitor: RDAP first, WHOIS fallback ────────────────────────────────

def _whois(days):
    return SimpleNamespace(
        expiration_date=datetime.now() + timedelta(days=days),
        registrar="WHOIS Registrar",
    )


def test_rdap_is_preferred_and_whois_never_called():
    future = (datetime.now(timezone.utc) + timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _get(_payload(expiry=future)), \
         patch("src.monitors.domain_monitor.whois.whois") as mock_whois:
        res = DomainMonitor().check_domain("example.com")

    assert res["source"] == "rdap"
    assert res["status"] == "ok"
    assert res["registrar"] == "Example Registrar, Inc."
    mock_whois.assert_not_called()


def test_whois_takes_over_when_rdap_has_no_record():
    with _get(None, status_code=404), \
         patch("src.monitors.domain_monitor.whois.whois", return_value=_whois(100)):
        res = DomainMonitor().check_domain("example.com")

    assert res["source"] == "whois"
    assert res["status"] == "ok"
    assert res["registrar"] == "WHOIS Registrar"


def test_whois_takes_over_when_rdap_is_unreachable():
    """Port 443 blocked, DNS broken, proxy refusing — all the same to us."""
    with patch("src.monitors.rdap.requests.get", side_effect=requests.ConnectionError("nope")), \
         patch("src.monitors.domain_monitor.whois.whois", return_value=_whois(5)):
        res = DomainMonitor().check_domain("example.com")

    assert res["source"] == "whois"
    assert res["status"] == "critical"


def test_use_rdap_false_skips_it_entirely():
    with patch("src.monitors.rdap.requests.get") as mock_get, \
         patch("src.monitors.domain_monitor.whois.whois", return_value=_whois(100)):
        res = DomainMonitor(use_rdap=False).check_domain("example.com")

    assert res["source"] == "whois"
    mock_get.assert_not_called()


def test_use_rdap_comes_from_config():
    assert DomainMonitor.from_config({}).use_rdap is True
    assert DomainMonitor.from_config({"use_rdap": False}).use_rdap is False
    assert DomainMonitor.from_config({"use_rdap": True}).use_rdap is True


def test_config_thresholds_survive_the_rdap_option():
    m = DomainMonitor.from_config({"use_rdap": False, "expiry_warning_days": 90,
                                   "expiry_critical_days": 60})
    assert (m.expiry_warning_days, m.expiry_critical_days, m.use_rdap) == (90, 60, False)


def test_both_paths_failing_is_an_error_result():
    with patch("src.monitors.rdap.requests.get", side_effect=requests.ConnectionError("nope")), \
         patch("src.monitors.domain_monitor.whois.whois", side_effect=Exception("port 43 blocked")):
        res = DomainMonitor().check_domain("example.com")

    assert res["status"] == "error"
    assert res["monitor"] == "domain"
    assert res["message"] == "Could not retrieve expiration date"
