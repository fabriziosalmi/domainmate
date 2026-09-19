"""
POST /analyze makes the host run WHOIS, TLS and HTTP probes against whatever
domain the caller names. These tests pin that the optional key protects the
write endpoints, leaves /metrics open for the container healthcheck, and
changes nothing when it is unset.
"""

import importlib

import pytest
from fastapi import HTTPException


def _api(monkeypatch, key=None):
    """Reimport the API module with DOMAINMATE_API_KEY set or cleared."""
    if key is None:
        monkeypatch.delenv("DOMAINMATE_API_KEY", raising=False)
    else:
        monkeypatch.setenv("DOMAINMATE_API_KEY", key)
    import api.api as module
    return importlib.reload(module)


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    """Leave the module as the rest of the suite expects to find it."""
    yield
    monkeypatch.delenv("DOMAINMATE_API_KEY", raising=False)
    import api.api
    importlib.reload(api.api)


# ── Unset: behaviour is exactly what it was ──────────────────────────────────

def test_no_key_configured_lets_everything_through(monkeypatch):
    api = _api(monkeypatch, key=None)
    assert api.API_KEY is None
    assert api.require_api_key(None) is None
    assert api.require_api_key("anything") is None


def test_empty_key_counts_as_unset(monkeypatch):
    api = _api(monkeypatch, key="")
    assert api.API_KEY is None
    assert api.require_api_key(None) is None


# ── Set: the header is required and must match ───────────────────────────────

def test_correct_key_is_accepted(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    assert api.require_api_key("s3cret") is None


def test_missing_header_is_rejected(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    with pytest.raises(HTTPException) as exc:
        api.require_api_key(None)
    assert exc.value.status_code == 401


def test_wrong_key_is_rejected(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    with pytest.raises(HTTPException) as exc:
        api.require_api_key("guess")
    assert exc.value.status_code == 401


def test_prefix_of_the_key_is_rejected(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    with pytest.raises(HTTPException):
        api.require_api_key("s3c")


def test_empty_header_is_rejected(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    with pytest.raises(HTTPException):
        api.require_api_key("")


# ── The dependency is wired where it belongs ─────────────────────────────────

def _dependency_names(app, path):
    route = next(r for r in app.routes if getattr(r, "path", None) == path)
    return {d.call.__name__ for d in route.dependant.dependencies if d.call}


def test_write_endpoints_require_the_key(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    for path in ("/analyze", "/notify/test"):
        assert "require_api_key" in _dependency_names(api.app, path), path


def test_metrics_stays_open_for_the_healthcheck(monkeypatch):
    api = _api(monkeypatch, key="s3cret")
    assert "require_api_key" not in _dependency_names(api.app, "/metrics")


def test_metrics_reports_whether_auth_is_on(monkeypatch):
    assert _api(monkeypatch, key="s3cret").get_metrics()["auth_required"] is True
    assert _api(monkeypatch, key=None).get_metrics()["auth_required"] is False
