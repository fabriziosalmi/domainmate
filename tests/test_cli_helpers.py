from src.cli import clean_domain, get_parent_domain, get_demo_data


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
