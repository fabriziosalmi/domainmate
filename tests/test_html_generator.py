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
    data = json.loads((reports_dir / "report.json").read_text())
    assert len(data) == len(SAMPLE)


def test_expired_cert_rendered_without_negative_days(tmp_path):
    _, reports_dir = _generate(tmp_path)
    html = (reports_dir / "index.html").read_text()
    assert "Expired 12 days ago" in html
    assert "-12 days remaining" not in html


def test_status_filter_and_footer_present(tmp_path):
    _, reports_dir = _generate(tmp_path)
    html = (reports_dir / "index.html").read_text()
    assert 'id="statusFilter"' in html
    assert "github.com/fabriziosalmi/domainmate" in html


def test_empty_results_do_not_crash(tmp_path):
    gen = HTMLGenerator(template_dir=str(tmp_path / "templates"), output_dir=str(tmp_path / "reports"))
    gen.generate([])
    assert (tmp_path / "reports" / "index.html").exists()
