"""Analyzer tests: deterministic checks produce evidence-backed findings."""

import asyncio

from app.analyzers.base import ScanContext
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.security.headers import (
    check_csp, check_frame_protection, check_hsts, check_https,
    check_permissions_policy, check_technology_disclosure,
    check_x_content_type_options,
)
from app.analyzers.performance.images import (
    check_images_missing_dimensions, check_large_images,
)
from app.analyzers.architecture.technology_detector import detect_technologies
from app.crawler.models import CrawledPage, CrawledResource

BASE = "https://example.com/"


def _page(html: str = "<html><body><h1>hi</h1></body></html>", headers=None) -> CrawledPage:
    return CrawledPage(
        url=BASE, status_code=200, content_type="text/html",
        headers=headers or {}, html=html, word_count=5,
    )


# ---- security headers -----------------------------------------------------

def test_https_check_flags_http():
    findings = check_https({"x-test": "1"}, "http://example.com/")
    assert any(f.rule_id == "SEC_HTTPS_ABSENT" for f in findings)
    assert findings[0].severity == "HIGH"


def test_hsts_missing():
    findings = check_hsts({})
    assert any(f.rule_id == "SEC_HSTS_MISSING" for f in findings)
    assert findings[0].evidence  # every finding carries evidence


def test_hsts_good_header_no_findings():
    good = "max-age=31536000; includeSubDomains; preload"
    assert check_hsts({"strict-transport-security": good}) == []


def test_csp_unsafe_inline_detected():
    findings = check_csp({"content-security-policy": "default-src 'self'; script-src 'unsafe-inline'"})
    assert any(f.rule_id == "SEC_CSP_UNSAFE_INLINE" for f in findings)


def test_frame_protection_missing():
    findings = check_frame_protection({})
    assert any(f.rule_id == "SEC_FRAME_PROTECTION_MISSING" for f in findings)


def test_xcto_and_permissions_and_disclosure():
    assert check_x_content_type_options({})
    assert check_permissions_policy({})
    disclosure = check_technology_disclosure({"x-powered-by": "Express/4.18.1"})
    assert any(f.rule_id == "SEC_TECH_DISCLOSURE" for f in disclosure)


# ---- performance ----------------------------------------------------------

def test_large_image_detected():
    big = CrawledResource(url="https://example.com/hero.png", resource_type="IMAGE", size_bytes=2 * 1024 * 1024)
    findings = check_large_images([big])
    assert any(f.rule_id == "PERF_LARGE_IMAGE" for f in findings)


def test_small_image_not_flagged():
    small = CrawledResource(url="https://example.com/icon.png", resource_type="IMAGE", size_bytes=1024)
    assert check_large_images([small]) == []


def test_images_missing_dimensions_needs_two_pages():
    p1 = _page('<img src="/a.png">')
    p2 = _page('<img src="/b.png">')
    findings = check_images_missing_dimensions([p1, p2])
    assert any(f.rule_id == "PERF_IMAGES_NO_DIMENSIONS" for f in findings)


# ---- technology detection -------------------------------------------------

def test_technology_detection_from_headers():
    pages = [_page(headers={"server": "nginx", "x-powered-by": "Express"})]
    tech = detect_technologies(pages)
    names = {t.name for t in tech}
    assert "Nginx" in names
    assert "Express" in names
    for t in tech:
        assert t.evidence  # every detection has evidence


def test_technology_detection_from_markup():
    pages = [_page('<div id="root"><script src="/react.js"></script></div>')]
    names = {t.name for t in detect_technologies(pages)}
    assert "React" in names


def test_no_false_positives_on_clean_page():
    pages = [_page("<html><body><p>Nothing here.</p></body></html>", headers={"server": "custom"})]
    assert detect_technologies(pages) == []


# ---- registry -------------------------------------------------------------

def test_registry_runs_all_without_crashing():
    context = ScanContext(
        scan_id=1, website_id=1, base_url=BASE,
        pages=[_page(html='<html lang="en"><head><title>T</title></head>'
                          '<body><img src="/big.png"><a href="/x">x</a></body></html>')],
        resources=[CrawledResource(url="https://example.com/big.png", resource_type="IMAGE", size_bytes=2_000_000)],
    )
    results, runs = asyncio.run(AnalyzerRegistry.run_all(context))
    assert len(runs) >= 5  # all registered analyzers ran
    for run in runs:
        assert run.status == "COMPLETED", f"{run.name} failed: {run.error}"
    # At least one finding should exist somewhere for this deliberately bad page.
    total = sum(len(r.findings) for r in results.values())
    assert total > 0
