"""SSRF protection tests — the most safety-critical unit tests."""

import pytest

from app.core.exceptions import ValidationError
from app.security.ssrf import (
    validate_resolved_ip, validate_url_target, check_hostname_safety,
)
from app.crawler.url_validator import validate_crawl_url


def test_validate_resolved_ip_blocks_private():
    for ip in ("127.0.0.1", "10.0.0.1", "172.16.5.5", "192.168.1.1",
               "169.254.169.254", "0.0.0.0", "::1", "fc00::1", "fe80::1"):
        with pytest.raises(ValidationError):
            validate_resolved_ip(ip)


def test_validate_resolved_ip_allows_public():
    validate_resolved_ip("8.8.8.8")
    validate_resolved_ip("1.1.1.1")
    validate_resolved_ip("2606:4700:4700::1111")


def test_hostname_safety_blocks_internal_hostnames():
    for host in ("localhost", "intranet", "internal", "corp", "db", "admin", "metadata.google.internal"):
        with pytest.raises(ValidationError):
            check_hostname_safety(host)


def test_hostname_safety_blocks_private_suffixes():
    for host in ("app.internal", "server.local", "router.lan", "db.corp"):
        with pytest.raises(ValidationError):
            check_hostname_safety(host)


def test_crawl_url_blocks_localhost():
    with pytest.raises(ValidationError):
        validate_crawl_url("http://localhost:8001/")
    with pytest.raises(ValidationError):
        validate_crawl_url("http://127.0.0.1/index.html")


def test_crawl_url_blocks_non_http():
    with pytest.raises(ValidationError):
        validate_crawl_url("file:///etc/passwd")
    with pytest.raises(ValidationError):
        validate_crawl_url("gopher://example.com/")


def test_crawl_url_blocks_credentials():
    with pytest.raises(ValidationError):
        validate_crawl_url("https://user:pass@example.com/")


def test_crawl_url_allow_internal_escape_hatch_demo_only():
    # The demo escape hatch must still reject non-http schemes and keep
    # structural checks active.
    with pytest.raises(ValidationError):
        validate_crawl_url("file:///etc/passwd", allow_internal=True)
    # localhost passes only with the explicit demo flag.
    url = validate_crawl_url("http://localhost:8001/index.html", allow_internal=True)
    assert url == "http://localhost:8001/index.html"


def test_validate_url_target_blocks_cloud_metadata():
    with pytest.raises(ValidationError):
        validate_url_target("http://169.254.169.254/latest/meta-data/")
