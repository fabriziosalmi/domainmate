"""
The two items the plan left in the backlog.

#14 SSLMonitor took a `port` argument and never passed it on, and the CLI
    threw a port away before the monitor could see one.
#15 The blacklist monitor reversed IPv4 octets on whatever the resolver
    returned first, so an IPv6 address produced a nonsense query and a
    CDN-hosted name went mostly unchecked.
"""

from unittest.mock import patch

import dns.resolver
import pytest

from src.cli import clean_domain, split_host_port
from src.constants import DEFAULT_TLS_PORT, MAX_IPS_PER_DOMAIN
from src.monitors.blacklist_monitor import BlacklistMonitor, rbl_query_name
from src.monitors.ssl_monitor import SSLMonitor

# ── #14: the port survives from config to socket ─────────────────────────────

@pytest.mark.parametrize("entry,host,port", [
    ("example.com", "example.com", None),
    ("mail.example.com:993", "mail.example.com", 993),
    ("https://example.com:8443/path", "example.com", 8443),
    ("  EXAMPLE.COM:8443  ", "example.com", 8443),
    ("example.com:443", "example.com", 443),
])
def test_split_host_port(entry, host, port):
    assert split_host_port(entry) == (host, port)


@pytest.mark.parametrize("entry", [
    "example.com:notaport",
    "example.com:0",
    "example.com:65536",
    "example.com:-1",
])
def test_bad_port_falls_back_rather_than_failing(entry):
    host, port = split_host_port(entry)
    assert host == "example.com"
    assert port is None


def test_clean_domain_still_returns_a_bare_hostname():
    """WHOIS, DNS and the RBLs must never be handed a port."""
    assert clean_domain("mail.example.com:993") == "mail.example.com"


def _connect_target(domain, **kwargs):
    with patch("src.monitors.ssl_monitor.socket.create_connection",
               side_effect=OSError("refused")) as sock:
        SSLMonitor().check_ssl(domain, **kwargs)
    return sock.call_args[0][0]


def test_port_reaches_the_socket():
    assert _connect_target("mail.example.com", port=993) == ("mail.example.com", 993)


def test_default_port_is_443():
    assert _connect_target("example.com") == ("example.com", DEFAULT_TLS_PORT)


def test_base_monitor_forwards_keyword_arguments():
    """The argument used to be swallowed by check() before _run_check saw it."""
    captured = {}

    class Probe(SSLMonitor):
        def _run_check(self, domain, port=DEFAULT_TLS_PORT):
            captured["port"] = port
            return {"monitor": "ssl", "status": "ok", "message": "stub"}

    Probe().check_ssl("example.com", port=8443)
    assert captured["port"] == 8443


# ── #15: IPv6 and every address, not just the first ──────────────────────────

def test_ipv4_query_reverses_the_octets():
    assert rbl_query_name("1.2.3.4") == "4.3.2.1"


def test_ipv6_query_reverses_the_nibbles():
    name = rbl_query_name("2001:db8::1")
    labels = name.split(".")
    assert len(labels) == 32, "an IPv6 DNSBL name is 32 nibbles"
    assert all(len(x) == 1 for x in labels)
    # the expanded address read backwards, one nibble at a time
    assert name.startswith("1.0.0.0.")
    assert name.endswith(".1.0.0.2")


def test_ipv4_mapped_is_asked_about_as_ipv4():
    """::ffff:1.2.3.4 is 1.2.3.4, and that is the form a DNSBL expects."""
    assert rbl_query_name("::ffff:1.2.3.4") == rbl_query_name("1.2.3.4") == "4.3.2.1"


def test_ipv6_nibbles_come_from_the_packed_bytes():
    """`.exploded` renders an IPv4-mapped address with a dotted quad on the end."""
    for ip in ("2001:db8::1", "::1", "fe80::200:5eff:fe00:5213"):
        labels = rbl_query_name(ip).split(".")
        assert len(labels) == 32
        assert all(len(x) == 1 and x in "0123456789abcdef" for x in labels), ip


def test_malformed_address_is_rejected():
    with pytest.raises(ValueError):
        rbl_query_name("not-an-ip")


class _Resolver:
    """Stands in for RobustResolver with a fixed answer per record type."""

    def __init__(self, a=(), aaaa=()):
        self._answers = {"A": list(a), "AAAA": list(aaaa)}

    def get_ips(self, domain, rdtype="A"):
        return self._answers.get(rdtype, [])


def _run(monitor, resolver, listed=()):
    """Run a check with resolution stubbed and a fixed set of listed names."""
    listed = set(listed)

    def resolve(query, rdtype):
        if query in listed:
            answer = type("R", (), {"to_text": lambda self: "127.0.0.2"})()
            return [answer]
        raise dns.resolver.NXDOMAIN()

    with patch("src.utils.dns_helpers.RobustResolver", return_value=resolver), \
         patch.object(monitor.system_resolver, "resolve", side_effect=resolve):
        return monitor.check_blacklist("example.com")


def test_every_address_is_checked_not_just_the_first():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver(a=["1.2.3.4", "5.6.7.8"]),
               listed={"8.7.6.5.rbl.test"})
    assert res["ips"] == ["1.2.3.4", "5.6.7.8"]
    assert res["status"] == "critical"
    assert res["listed_ips"] == ["5.6.7.8"], "the second address was the listed one"


def test_ipv6_only_domain_is_checked_instead_of_erroring():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver(aaaa=["2001:db8::1"]))
    assert res["status"] == "ok"
    assert res["ips"] == ["2001:db8::1"]


def test_dual_stack_checks_both_families():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver(a=["1.2.3.4"], aaaa=["2001:db8::1"]))
    assert res["ips"] == ["1.2.3.4", "2001:db8::1"]


def test_duplicate_addresses_are_checked_once():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver(a=["1.2.3.4", "1.2.3.4"]))
    assert res["ips"] == ["1.2.3.4"]


def test_address_count_is_capped():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    many = [f"10.0.0.{i}" for i in range(MAX_IPS_PER_DOMAIN + 3)]
    res = _run(mon, _Resolver(a=many))
    assert len(res["ips"]) == MAX_IPS_PER_DOMAIN


def test_unresolvable_domain_is_an_error():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver())
    assert res["status"] == "error"
    assert res["message"] == "Could not resolve domain"


def test_listings_say_which_rbl_listed_which_address():
    mon = BlacklistMonitor(rbls=["one.test", "two.test"])
    res = _run(mon, _Resolver(a=["1.2.3.4", "5.6.7.8"]),
               listed={"4.3.2.1.one.test", "8.7.6.5.one.test", "8.7.6.5.two.test"})
    assert res["listings"] == {
        "one.test": ["1.2.3.4", "5.6.7.8"],
        "two.test": ["5.6.7.8"],
    }
    assert sorted(res["listed_in"]) == ["one.test", "two.test"]


def test_ip_field_is_kept_for_existing_consumers():
    mon = BlacklistMonitor(rbls=["rbl.test"])
    res = _run(mon, _Resolver(a=["1.2.3.4", "5.6.7.8"]))
    assert res["ip"] == "1.2.3.4"
