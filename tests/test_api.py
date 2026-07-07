import pytest
from pydantic import ValidationError

from api.api import AnalyzeRequest, get_metrics, app


def test_valid_domain_normalized():
    req = AnalyzeRequest(domain="  EXAMPLE.Com ")
    assert req.domain == "example.com"


def test_subdomain_accepted():
    assert AnalyzeRequest(domain="a.b.example.co.uk").domain == "a.b.example.co.uk"


@pytest.mark.parametrize("bad", ["", "   ", "no-dot", "not a domain", "http://example.com", "-bad.com", "example."])
def test_invalid_domain_rejected(bad):
    with pytest.raises(ValidationError):
        AnalyzeRequest(domain=bad)


def test_metrics_shape():
    m = get_metrics()
    assert m["status"] == "healthy"
    assert m["monitors_active"] == 5
    assert m["version"] == app.version
