"""
The CLI used to run every check one after another: 7 domains x 5 monitors was
35 blocking network calls in series, while api.py had been gathering them in
threads all along. These tests pin the concurrency, the bound on it, and the
fact that results stay in a deterministic order whatever finishes first.
"""

import asyncio
import threading
import time

import pytest

from src.scanner import MONITOR_ORDER, scan_all, scan_domain

CONFIG = {
    "monitors": {name: {"enabled": True} for name in MONITOR_ORDER},
}


class _RecordingMonitor:
    """A stand-in check that sleeps, and records how many ran at once."""

    def __init__(self, tracker, name, delay=0.05):
        self.tracker = tracker
        self.name = name
        self.delay = delay

    def __call__(self, target, **kwargs):
        # **kwargs mirrors the real checks: SSLMonitor.check_ssl takes a port
        self.tracker.enter()
        try:
            time.sleep(self.delay)
            return {"monitor": self.name, "status": "ok", "message": f"checked {target}"}
        finally:
            self.tracker.leave()


class _Tracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.total = 0

    def enter(self):
        with self.lock:
            self.active += 1
            self.total += 1
            self.peak = max(self.peak, self.active)

    def leave(self):
        with self.lock:
            self.active -= 1


def _monitors(tracker, delay=0.05):
    mons = {}
    for name in MONITOR_ORDER:
        stub = type("Stub", (), {})()
        call = _RecordingMonitor(tracker, name, delay)
        setattr(stub, f"check_{name}", call)
        mons[name] = stub
    return mons


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    """Resolution is a network call; every domain resolves to itself here."""
    monkeypatch.setattr("src.cli.get_connectable_hostname", lambda d: d)


# ── Concurrency ──────────────────────────────────────────────────────────────

def test_checks_actually_run_in_parallel():
    tracker = _Tracker()
    domains = [f"d{i}.com" for i in range(4)]
    started = time.monotonic()
    asyncio.run(scan_all(domains, _monitors(tracker), CONFIG, concurrency=20))
    elapsed = time.monotonic() - started

    assert tracker.total == 4 * len(MONITOR_ORDER)
    assert tracker.peak > 1, "checks ran one at a time"
    # 20 checks x 50ms would be 1.0s in series
    assert elapsed < 0.6, f"scan took {elapsed:.2f}s, too close to sequential"


def test_concurrency_is_bounded():
    tracker = _Tracker()
    domains = [f"d{i}.com" for i in range(6)]
    asyncio.run(scan_all(domains, _monitors(tracker), CONFIG, concurrency=3))
    assert tracker.peak <= 3, f"peak {tracker.peak} exceeded the limit of 3"


def test_concurrency_of_one_is_still_valid():
    tracker = _Tracker()
    results = asyncio.run(scan_all(["a.com", "b.com"], _monitors(tracker, delay=0.01),
                                   CONFIG, concurrency=1))
    assert tracker.peak == 1
    assert len(results) == 2 * len(MONITOR_ORDER)


def test_zero_concurrency_does_not_deadlock():
    tracker = _Tracker()
    results = asyncio.run(scan_all(["a.com"], _monitors(tracker, delay=0.01),
                                   CONFIG, concurrency=0))
    assert len(results) == len(MONITOR_ORDER)


# ── Deterministic ordering ───────────────────────────────────────────────────

def test_results_follow_config_order_not_completion_order():
    """The slowest domain is first in the config, so it must stay first."""
    tracker = _Tracker()
    mons = _monitors(tracker, delay=0.01)
    slow = _RecordingMonitor(tracker, "domain", delay=0.15)
    setattr(mons["domain"], "check_domain", slow)

    domains = ["slow.com", "fast-a.com", "fast-b.com"]
    results = asyncio.run(scan_all(domains, mons, CONFIG, concurrency=20))

    seen = []
    for r in results:
        if r["domain"] not in seen:
            seen.append(r["domain"])
    assert seen == domains


def test_monitors_keep_their_order_within_a_domain():
    tracker = _Tracker()
    results = asyncio.run(scan_all(["a.com"], _monitors(tracker, delay=0.01),
                                   CONFIG, concurrency=20))
    assert [r["monitor"] for r in results] == list(MONITOR_ORDER)


def test_two_runs_produce_the_same_order():
    tracker = _Tracker()
    domains = ["c.com", "a.com", "b.com"]
    first = asyncio.run(scan_all(domains, _monitors(tracker, 0.01), CONFIG, concurrency=20))
    second = asyncio.run(scan_all(domains, _monitors(tracker, 0.01), CONFIG, concurrency=20))
    def key(rs):
        return [(r["domain"], r["monitor"]) for r in rs]

    assert key(first) == key(second)


# ── Behaviour preserved from the sequential loop ─────────────────────────────

def test_disabled_monitors_are_skipped():
    tracker = _Tracker()
    config = {"monitors": {"domain": {"enabled": True}, "ssl": {"enabled": False},
                           "dns": {"enabled": True}, "security": {"enabled": False},
                           "blacklist": {"enabled": False}}}
    results = asyncio.run(scan_all(["a.com"], _monitors(tracker, 0.01), config, concurrency=5))
    assert [r["monitor"] for r in results] == ["domain", "dns"]


def test_subdomain_uses_parent_and_says_so():
    tracker = _Tracker()
    results = asyncio.run(scan_all(["www.example.com"], _monitors(tracker, 0.01),
                                   CONFIG, concurrency=5))
    by = {r["monitor"]: r for r in results}
    assert "checked example.com" in by["domain"]["message"]
    assert by["domain"]["message"].startswith("(Parent: example.com)")
    assert by["dns"]["message"].startswith("(Parent: example.com)")
    # blacklist keeps the original label and target
    assert "checked www.example.com" in by["blacklist"]["message"]
    assert all(r["domain"] == "www.example.com" for r in results)


def test_unresolvable_host_marks_ssl_and_security_critical(monkeypatch):
    monkeypatch.setattr("src.cli.get_connectable_hostname", lambda d: None)
    tracker = _Tracker()
    results = asyncio.run(scan_all(["nope.invalid"], _monitors(tracker, 0.01),
                                   CONFIG, concurrency=5))
    by = {r["monitor"]: r for r in results}
    for name in ("ssl", "security"):
        assert by[name]["status"] == "critical"
        assert by[name]["message"] == "DNS Resolution Failed"
    # the checks that do not need a connection still ran
    assert by["domain"]["status"] == "ok"
    assert by["blacklist"]["status"] == "ok"


def test_one_failing_monitor_does_not_lose_the_others():
    tracker = _Tracker()
    mons = _monitors(tracker, delay=0.01)

    def boom(target, **kwargs):
        raise RuntimeError("monitor exploded")

    setattr(mons["ssl"], "check_ssl", boom)
    results = asyncio.run(scan_all(["a.com"], mons, CONFIG, concurrency=5))
    assert [r["monitor"] for r in results] == ["domain", "dns", "security", "blacklist"]


def test_one_failing_domain_does_not_lose_the_scan(monkeypatch):
    tracker = _Tracker()
    real = scan_domain

    async def flaky(raw_domain, *args, **kwargs):
        if raw_domain == "bad.com":
            raise RuntimeError("domain exploded")
        return await real(raw_domain, *args, **kwargs)

    monkeypatch.setattr("src.scanner.scan_domain", flaky)
    results = asyncio.run(scan_all(["a.com", "bad.com", "b.com"],
                                   _monitors(tracker, 0.01), CONFIG, concurrency=5))
    assert {r["domain"] for r in results} == {"a.com", "b.com"}


def test_empty_domain_list_returns_nothing():
    tracker = _Tracker()
    assert asyncio.run(scan_all([], _monitors(tracker), CONFIG, concurrency=5)) == []
