"""Image optimization checks (deterministic)."""

from app.analyzers.base import EvidenceDraft, FindingDraft

LARGE_IMAGE_BYTES = 300 * 1024  # 300 KB
HUGE_IMAGE_BYTES = 1 * 1024 * 1024  # 1 MB


def check_large_images(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    images = [
        r for r in resources
        if r.resource_type == "IMAGE" and (r.size_bytes or 0) >= LARGE_IMAGE_BYTES
    ]
    images.sort(key=lambda r: -(r.size_bytes or 0))
    for r in images[:8]:
        size_kb = (r.size_bytes or 0) / 1024
        findings.append(
            FindingDraft(
                rule_id="PERF_LARGE_IMAGE",
                title=f"Oversized image ({size_kb:.0f} KB)",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    f"Image {r.url} is {size_kb:.0f} KB. Images should be compressed "
                    "and delivered in modern formats (WebP/AVIF) at display size."
                ),
                affected_url=r.url,
                evidence=[EvidenceDraft("RESOURCE", r.url, f"size_bytes={r.size_bytes}",
                                         {"size_bytes": r.size_bytes})],
            )
        )
    return findings


def check_images_missing_dimensions(pages) -> list[FindingDraft]:
    """Detect <img> elements without width/height attributes (from HTML)."""
    findings: list[FindingDraft] = []
    missing: list[str] = []
    for page in pages:
        if not page.html:
            continue
        from app.crawler.parser import parse_html
        parsed = parse_html(page.html, page.url)
        if not parsed:
            continue
        for img in parsed.soup.find_all("img"):
            if not img.get("width") and not img.get("height") and img.get("src"):
                missing.append(page.url)
                break  # one signal per page
    if len(missing) >= 2:
        findings.append(
            FindingDraft(
                rule_id="PERF_IMAGES_NO_DIMENSIONS",
                title=f"Images missing width/height attributes on {len(missing)} page(s)",
                severity="LOW",
                confidence=0.85,
                impact="LOW",
                effort="LOW",
                description=(
                    "Images without explicit dimensions cause layout shifts during "
                    "loading (CLS risk)."
                ),
                affected_url=missing[0],
                evidence=[EvidenceDraft("HTML_ELEMENT", missing[0], f"pages={len(missing)}")],
            )
        )
    return findings
