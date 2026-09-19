import json

import pytest

from src.cli import _ArgumentParser, clean_domain, compute_exit_code, emit_json, get_demo_data, get_parent_domain
from src.constants import EXIT_CRITICAL, EXIT_ERROR, EXIT_OK, EXIT_WARNING


def test_clean_domain_strips_protocol_and_path():
    assert clean_domain("https://www.google.com/foo?q=1") == "www.google.com"


def test_clean_domain_strips_port():
    assert clean_domain("example.com:8443") == "example.com"


def test_clean_domain_lowercases_and_trims():
    assert clean_domain("  EXAMPLE.COM  ") == "example.com"


def test_clean_domain_plain_passthrough():
    assert clean_domain("sub.example.org") == "sub.example.org"


def test_get_parent_domain_from_subdomain():
    assert get_parent_domain("www.example.com") == "example.com"
    assert get_parent_domain("a.b.example.com") == "example.com"


def test_get_parent_domain_root_unchanged():
    assert get_parent_domain("example.com") == "example.com"


def test_demo_data_shape():
    results = get_demo_data()
    assert results
    valid_statuses = {"ok", "warning", "critical", "error"}
    for r in results:
        assert r["status"] in valid_statuses
        assert r["domain"]
        assert r["monitor"] in {"domain", "ssl", "dns", "blacklist"}


# ── Exit-code contract (--fail-on) ───────────────────────────────────────────





def _r(status):
    return {"domain": "a.com", "monitor": "ssl", "status": status}


CLEAN = [_r("ok"), _r("ok")]
WARNED = [_r("ok"), _r("warning")]
CRITICAL = [_r("ok"), _r("warning"), _r("critical")]
ERRORED = [_r("ok"), _r("error")]


@pytest.mark.parametrize("results", [[], CLEAN, WARNED, CRITICAL, ERRORED])
def test_fail_on_never_always_succeeds(results):
    """The default must not change the exit code of existing pipelines."""
    assert compute_exit_code(results, "never") == EXIT_OK


@pytest.mark.parametrize(
    "results,expected",
    [
        ([], EXIT_OK),
        (CLEAN, EXIT_OK),
        (WARNED, EXIT_WARNING),
        (CRITICAL, EXIT_CRITICAL),
        (ERRORED, EXIT_CRITICAL),
    ],
)
def test_fail_on_warning(results, expected):
    assert compute_exit_code(results, "warning") == expected


@pytest.mark.parametrize(
    "results,expected",
    [
        ([], EXIT_OK),
        (CLEAN, EXIT_OK),
        (WARNED, EXIT_OK),  # warnings do not fail at this level
        (CRITICAL, EXIT_CRITICAL),
        (ERRORED, EXIT_CRITICAL),
    ],
)
def test_fail_on_critical(results, expected):
    assert compute_exit_code(results, "critical") == expected


def test_critical_outranks_warning():
    """A critical finding reports 2 even when the threshold is 'warning'."""
    assert compute_exit_code(CRITICAL, "warning") == EXIT_CRITICAL


def test_error_status_counts_as_critical():
    assert compute_exit_code(ERRORED, "critical") == EXIT_CRITICAL


def test_results_without_status_do_not_fail():
    assert compute_exit_code([{"domain": "a.com"}], "warning") == EXIT_OK


# ── --json output ────────────────────────────────────────────────────────────

def test_emit_json_writes_parseable_stdout(capsys):
    emit_json(CRITICAL)
    parsed = json.loads(capsys.readouterr().out)
    assert [r["status"] for r in parsed] == ["ok", "warning", "critical"]


def test_emit_json_preserves_non_ascii(capsys):
    emit_json([{"domain": "exämple.com", "registrar": "Registrar Ünïcode"}])
    out = capsys.readouterr().out
    assert "exämple.com" in out
    assert json.loads(out)[0]["registrar"] == "Registrar Ünïcode"


# ── Usage errors stay distinguishable from findings ──────────────────────────

def test_usage_error_exits_with_error_code(capsys):
    parser = _ArgumentParser(prog="domainmate")
    parser.add_argument("--fail-on", choices=["never", "warning", "critical"])
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--fail-on", "bogus"])
    assert exc.value.code == EXIT_ERROR, "usage errors must not look like critical findings"
