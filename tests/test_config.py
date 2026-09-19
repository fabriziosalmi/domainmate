"""
The keys these tests cover were all documented in README.md and config.yaml
while no code read them. Each test asserts that a setting actually reaches the
monitor that is supposed to use it.
"""

import textwrap

import pytest

from src.config import (
    config_path,
    load_config,
    monitor_config,
    monitor_enabled,
    report_setting,
    validate_config,
)
from src.constants import DEFAULT_RBLS, EXPIRY_CRITICAL_DAYS, EXPIRY_WARNING_DAYS
from src.monitors.blacklist_monitor import BlacklistMonitor
from src.monitors.dns_monitor import DNSMonitor
from src.monitors.domain_monitor import DomainMonitor
from src.monitors.ssl_monitor import SSLMonitor

FULL = textwrap.dedent("""
    domains:
      - example.com
    monitors:
      domain:
        enabled: true
        expiry_warning_days: 90
        expiry_critical_days: 60
      ssl:
        enabled: true
        expiry_warning_days: 21
        expiry_critical_days: 3
      dns:
        enabled: false
        required_records: [spf, dmarc, mx]
      blacklist:
        enabled: true
        rbls: [zen.spamhaus.org, custom.rbl.example]
    reports:
      output_dir: /tmp/dm-reports
      retention_days: 14
""")


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv("DOMAINMATE_CONFIG_FILE", raising=False)
    p = tmp_path / "config.yaml"
    p.write_text(FULL, encoding="utf-8")
    return load_config(str(p))


# ── Loading and precedence ───────────────────────────────────────────────────

def test_env_var_wins_over_cli_flag(monkeypatch):
    monkeypatch.setenv("DOMAINMATE_CONFIG_FILE", "/from/env.yaml")
    assert config_path("/from/flag.yaml") == "/from/env.yaml"


def test_cli_flag_used_when_env_unset(monkeypatch):
    monkeypatch.delenv("DOMAINMATE_CONFIG_FILE", raising=False)
    assert config_path("/from/flag.yaml") == "/from/flag.yaml"


def test_empty_file_is_an_empty_config(tmp_path, monkeypatch):
    monkeypatch.delenv("DOMAINMATE_CONFIG_FILE", raising=False)
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    assert load_config(str(p)) == {}


def test_non_mapping_config_is_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("DOMAINMATE_CONFIG_FILE", raising=False)
    p = tmp_path / "list.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(str(p))


# ── Unknown keys are reported, not silently dropped ─────────────────────────

def test_unknown_keys_are_flagged():
    unknown = validate_config({
        "domains": [],
        "typo_at_top": 1,
        "monitors": {"domain": {"enabled": True, "expiry_warnings_days": 30},
                     "nosuchmonitor": {}},
        "reports": {"output_dir": "x", "retenton_days": 5},
    })
    assert set(unknown) == {
        "typo_at_top",
        "monitors.domain.expiry_warnings_days",
        "monitors.nosuchmonitor",
        "reports.retenton_days",
    }


def test_valid_config_flags_nothing(cfg):
    assert validate_config(cfg) == []


# ── Accessors ────────────────────────────────────────────────────────────────

def test_monitor_enabled_reads_the_section(cfg):
    assert monitor_enabled(cfg, "domain") is True
    assert monitor_enabled(cfg, "dns") is False
    assert monitor_enabled(cfg, "absent") is False


def test_report_setting_with_default(cfg):
    assert report_setting(cfg, "output_dir") == "/tmp/dm-reports"
    assert report_setting(cfg, "retention_days") == 14
    assert report_setting({}, "output_dir", "reports") == "reports"


# ── Thresholds actually reach the monitors ───────────────────────────────────

def test_domain_thresholds_come_from_config(cfg):
    m = DomainMonitor.from_config(monitor_config(cfg, "domain"))
    assert (m.expiry_warning_days, m.expiry_critical_days) == (90, 60)
    # With the built-in 30/7 these would both be "ok"
    assert m.get_expiry_status(75) == "warning"
    assert m.get_expiry_status(50) == "critical"
    assert m.get_expiry_status(120) == "ok"


def test_ssl_thresholds_come_from_config(cfg):
    m = SSLMonitor.from_config(monitor_config(cfg, "ssl"))
    assert (m.expiry_warning_days, m.expiry_critical_days) == (21, 3)
    assert m.get_expiry_status(10) == "warning"
    assert m.get_expiry_status(2) == "critical"


def test_monitors_fall_back_to_constants_without_config():
    m = DomainMonitor()
    assert m.expiry_warning_days == EXPIRY_WARNING_DAYS
    assert m.expiry_critical_days == EXPIRY_CRITICAL_DAYS
    assert DomainMonitor.from_config({}).expiry_warning_days == EXPIRY_WARNING_DAYS
    assert DomainMonitor.from_config(None).expiry_warning_days == EXPIRY_WARNING_DAYS


def test_expired_is_critical_at_any_threshold():
    assert DomainMonitor(expiry_warning_days=90, expiry_critical_days=60).get_expiry_status(-5) == "critical"


# ── required_records ─────────────────────────────────────────────────────────

def test_required_records_come_from_config(cfg):
    assert DNSMonitor.from_config(monitor_config(cfg, "dns")).required_records == ["spf", "dmarc", "mx"]


def test_required_records_default_to_spf_and_dmarc():
    assert DNSMonitor().required_records == ["spf", "dmarc"]
    assert DNSMonitor.from_config({}).required_records == ["spf", "dmarc"]


def test_unsupported_record_is_dropped_not_silently_accepted():
    # DKIM needs a selector the config does not carry
    assert DNSMonitor(required_records=["spf", "dkim"]).required_records == ["spf"]


def test_required_records_are_normalised_and_deduped():
    assert DNSMonitor(required_records=[" SPF ", "spf", "CAA"]).required_records == ["spf", "caa"]


# ── rbls ─────────────────────────────────────────────────────────────────────

def test_rbls_come_from_config(cfg):
    assert BlacklistMonitor.from_config(monitor_config(cfg, "blacklist")).rbls == [
        "zen.spamhaus.org", "custom.rbl.example",
    ]


def test_rbls_default_to_the_built_in_list():
    assert BlacklistMonitor().rbls == list(DEFAULT_RBLS)
    assert BlacklistMonitor.from_config({}).rbls == list(DEFAULT_RBLS)


def test_config_rbls_do_not_mutate_the_shared_default():
    BlacklistMonitor(rbls=["only.one"]).rbls.append("another")
    assert BlacklistMonitor().rbls == list(DEFAULT_RBLS)
