import glob
import json
import os
import re
from datetime import datetime, timedelta, timezone

from src.reporting.html_generator import (
    HISTORY_PREFIX,
    HISTORY_STAMP,
    PACKAGED_TEMPLATE_DIR,
    TEMPLATE_NAME,
    HTMLGenerator,
)

SAMPLE = [
    {"domain": "a.com", "monitor": "ssl", "status": "ok", "message": "Expires in 100 days",
     "days_until_expiry": 100, "expiration_date": "2026-10-15"},
    {"domain": "a.com", "monitor": "dns", "status": "warning", "message": "Missing: DMARC"},
    {"domain": "b.org", "monitor": "ssl", "status": "critical", "message": "Expired 12 days ago",
     "days_until_expiry": -12, "expiration_date": "2026-06-25"},
    {"domain": "b.org", "monitor": "domain", "status": "error", "message": "WHOIS failed"},
]


def _generate(tmp_path):
    gen = HTMLGenerator(template_dir=str(tmp_path / "templates"), output_dir=str(tmp_path / "reports"))
    return gen.generate(SAMPLE), tmp_path / "reports"


def test_generates_html_and_json(tmp_path):
    output_file, reports_dir = _generate(tmp_path)
    assert (reports_dir / "index.html").exists()
    data = json.loads((reports_dir / "report.json").read_text(encoding="utf-8"))
    assert len(data) == len(SAMPLE)


def test_expired_cert_rendered_without_negative_days(tmp_path):
    _, reports_dir = _generate(tmp_path)
    html = (reports_dir / "index.html").read_text(encoding="utf-8")
    assert "Expired 12 days ago" in html
    assert "-12 days remaining" not in html


def test_status_filter_and_footer_present(tmp_path):
    _, reports_dir = _generate(tmp_path)
    html = (reports_dir / "index.html").read_text(encoding="utf-8")
    assert 'id="statusFilter"' in html
    assert "github.com/fabriziosalmi/domainmate" in html


def test_empty_results_do_not_crash(tmp_path):
    gen = HTMLGenerator(template_dir=str(tmp_path / "templates"), output_dir=str(tmp_path / "reports"))
    gen.generate([])
    assert (tmp_path / "reports" / "index.html").exists()


# ── The template is the user's, not the generator's ──────────────────────────
#
# HTMLGenerator used to rewrite report.html on every instantiation, so any
# customisation was destroyed the first time the tool ran.




def test_custom_template_dir_is_seeded_once(tmp_path):
    templates = tmp_path / "templates"
    HTMLGenerator(template_dir=str(templates), output_dir=str(tmp_path / "r"))
    seeded = templates / TEMPLATE_NAME
    assert seeded.exists()
    assert seeded.read_text(encoding="utf-8") == (
        (tmp_path / "templates" / TEMPLATE_NAME).read_text(encoding="utf-8")
    )


def test_existing_template_is_never_overwritten(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / TEMPLATE_NAME).write_text("<p>{{ timestamp }} mine</p>", encoding="utf-8")

    for _ in range(3):
        gen = HTMLGenerator(template_dir=str(templates), output_dir=str(tmp_path / "r"))
        gen.generate(SAMPLE)

    assert (templates / TEMPLATE_NAME).read_text(encoding="utf-8") == "<p>{{ timestamp }} mine</p>"
    assert "mine" in (tmp_path / "r" / "index.html").read_text(encoding="utf-8")


def test_packaged_template_is_used_by_default(tmp_path):
    gen = HTMLGenerator(output_dir=str(tmp_path / "r"))
    assert gen.template_dir == PACKAGED_TEMPLATE_DIR
    assert os.path.exists(os.path.join(PACKAGED_TEMPLATE_DIR, TEMPLATE_NAME))


# ── "Self-contained" has to be true ──────────────────────────────────────────

def _report_html(tmp_path):
    HTMLGenerator(output_dir=str(tmp_path / "r")).generate(SAMPLE)
    return (tmp_path / "r" / "index.html").read_text(encoding="utf-8")


def test_report_pulls_no_remote_assets(tmp_path):
    html = _report_html(tmp_path)
    assert "<script src=" not in html, "the report must not load a remote script"
    assert 'rel="stylesheet"' not in html, "the report must not load a remote stylesheet"


def test_report_does_not_depend_on_jquery_datatables_or_bootstrap(tmp_path):
    html = _report_html(tmp_path).lower()
    for gone in ("jquery", "datatables", "bootstrap", "cdn.", "cdnjs"):
        assert gone not in html, f"{gone} is still referenced by the report"


def test_report_carries_its_own_behaviour(tmp_path):
    html = _report_html(tmp_path)
    # Sorting, search, grouping and the status filter all ship inline
    assert 'id="searchBox"' in html
    assert 'id="statusFilter"' in html
    assert 'data-sort="status"' in html
    assert "function draw()" in html


def test_rows_expose_the_data_the_script_filters_on(tmp_path):
    html = _report_html(tmp_path)
    for attr in ("data-domain=", "data-monitor=", "data-status=", "data-expiry="):
        assert attr in html


# ── Report history and retention ─────────────────────────────────────────────
#
# reports.retention_days was documented as "Days to keep old reports (cleanup)"
# while nothing kept or removed anything: every run overwrote the same two
# files, so there was no history to prune.




def _snapshots(reports_dir):
    return sorted(os.path.basename(p) for p in
                  glob.glob(os.path.join(str(reports_dir), f"{HISTORY_PREFIX}*.json")))


def _plant(reports_dir, age_days, now=None):
    """Write a snapshot stamped `age_days` in the past."""
    now = now or datetime.now(timezone.utc)
    stamp = (now - timedelta(days=age_days)).strftime(HISTORY_STAMP)
    path = reports_dir / f"{HISTORY_PREFIX}{stamp}.json"
    path.write_text("[]", encoding="utf-8")
    return path


def test_each_run_leaves_a_snapshot(tmp_path):
    out = tmp_path / "r"
    HTMLGenerator(output_dir=str(out)).generate(SAMPLE)
    snaps = _snapshots(out)
    assert len(snaps) == 1
    assert re.fullmatch(r"report-\d{8}-\d{6}\.json", snaps[0])


def test_snapshot_holds_the_same_results_as_report_json(tmp_path):
    out = tmp_path / "r"
    HTMLGenerator(output_dir=str(out)).generate(SAMPLE)
    snapshot = json.loads((out / _snapshots(out)[0]).read_text(encoding="utf-8"))
    assert snapshot == json.loads((out / "report.json").read_text(encoding="utf-8"))


def test_latest_files_still_describe_the_last_run(tmp_path):
    out = tmp_path / "r"
    gen = HTMLGenerator(output_dir=str(out))
    gen.generate(SAMPLE)
    gen.generate([{"domain": "z.com", "monitor": "dns", "status": "ok", "message": "later"}])
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))[0]["domain"] == "z.com"


def test_retention_unset_keeps_everything(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    for age in (1, 40, 400):
        _plant(out, age)
    HTMLGenerator(output_dir=str(out), retention_days=None).generate(SAMPLE)
    assert len(_snapshots(out)) == 4  # three planted plus this run


def test_retention_removes_only_what_is_too_old(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    fresh = _plant(out, 5)
    stale = _plant(out, 40)
    gen = HTMLGenerator(output_dir=str(out), retention_days=30)
    gen.generate(SAMPLE)
    names = _snapshots(out)
    assert fresh.name in names
    assert stale.name not in names


def test_retention_zero_keeps_only_today(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    yesterday = _plant(out, 1)
    HTMLGenerator(output_dir=str(out), retention_days=0).generate(SAMPLE)
    assert yesterday.name not in _snapshots(out)
    assert len(_snapshots(out)) == 1


def test_retention_never_touches_the_current_files(tmp_path):
    out = tmp_path / "r"
    HTMLGenerator(output_dir=str(out), retention_days=0).generate(SAMPLE)
    assert (out / "index.html").exists()
    assert (out / "report.json").exists()


def test_unrelated_json_files_are_left_alone(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    bystander = out / "notification_state.json"
    bystander.write_text("{}", encoding="utf-8")
    odd = out / "report-not-a-timestamp.json"
    odd.write_text("[]", encoding="utf-8")
    _plant(out, 90)

    HTMLGenerator(output_dir=str(out), retention_days=1).generate(SAMPLE)
    assert bystander.exists()
    assert odd.exists()


def test_invalid_retention_is_reported_and_keeps_everything(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    old = _plant(out, 400)
    for bad in (-1, "thirty", 1.5):
        gen = HTMLGenerator(output_dir=str(out), retention_days=bad)
        assert gen.prune_history() == []
    assert old.exists()


def test_prune_is_idempotent(tmp_path):
    out = tmp_path / "r"
    out.mkdir()
    _plant(out, 90)
    gen = HTMLGenerator(output_dir=str(out), retention_days=30)
    assert len(gen.prune_history()) == 1
    assert gen.prune_history() == []
