import json

from src.reporting.html_generator import HTMLGenerator


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

import os

from src.reporting.html_generator import PACKAGED_TEMPLATE_DIR, TEMPLATE_NAME, HTMLGenerator


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
