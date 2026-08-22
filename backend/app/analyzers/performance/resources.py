"""Resource-level performance checks (deterministic)."""

from app.analyzers.base import EvidenceDraft, FindingDraft

LARGE_RESOURCE_BYTES = 500 * 1024  # 500 KB
HUGE_RESOURCE_BYTES = 2 * 1024 * 1024  # 2 MB
MANY_REQUESTS = 60
LARGE_PAGE_BYTES = 1.5 * 1024 * 1024


def check_page_weight(pages) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if not pages:
        return findings
    total_html = sum(p.html_size or 0 for p in pages)
    if total_html > LARGE_PAGE_BYTES:
        findings.append(
            FindingDraft(
                rule_id="PERF_LARGE_HTML",
                title="Large HTML payload",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    f"Total HTML payload across {len(pages)} crawled page(s) is "
                    f"{total_html / 1024 / 1024:.1f} MB. Large HTML slows parsing and rendering."
                ),
                evidence=[EvidenceDraft("METRIC", "pages", f"html_bytes={total_html}",
                                         {"bytes": total_html, "pages": len(pages)})],
            )
        )
    return findings


def check_resource_sizes(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    large = [r for r in resources if (r.size_bytes or 0) >= HUGE_RESOURCE_BYTES]
    large.sort(key=lambda r: -(r.size_bytes or 0))
    for r in large[:5]:
        size_mb = (r.size_bytes or 0) / 1024 / 1024
        findings.append(
            FindingDraft(
                rule_id="PERF_HUGE_RESOURCE",
                title=f"Very large {r.resource_type.lower()} resource ({size_mb:.1f} MB)",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    f"{r.url} weighs {size_mb:.1f} MB. Large resources increase load "
                    "time and mobile data usage."
                ),
                affected_url=r.url,
                evidence=[EvidenceDraft("RESOURCE", r.url, f"size_bytes={r.size_bytes}",
                                         {"size_bytes": r.size_bytes, "type": r.resource_type})],
            )
        )
    return findings


def check_request_count(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    total = len(resources)
    if total >= MANY_REQUESTS:
        findings.append(
            FindingDraft(
                rule_id="PERF_TOO_MANY_REQUESTS",
                title=f"High number of resource requests ({total})",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    f"The crawled pages reference {total} resources. Each request adds "
                    "network round-trips and latency."
                ),
                evidence=[EvidenceDraft("METRIC", "resources", f"count={total}", {"count": total})],
            )
        )
    return findings


def check_third_party_requests(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    external = [r for r in resources if r.is_external]
    if len(external) >= 10:
        findings.append(
            FindingDraft(
                rule_id="PERF_MANY_THIRD_PARTY_REQUESTS",
                title=f"High third-party request count ({len(external)})",
                severity="MEDIUM",
                confidence=0.9,
                impact="HIGH",
                effort="HIGH",
                description=(
                    f"{len(external)} of {len(resources)} resource requests go to "
                    "third-party domains. Third-party scripts block rendering and "
                    "add latency you cannot control."
                ),
                evidence=[EvidenceDraft("METRIC", "resources", f"external_count={len(external)}",
                                         {"count": len(external)})],
            )
        )
    return findings


def check_render_blocking_scripts(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    render_blocking = [
        r for r in resources
        if r.resource_type == "JS" and not r.is_external
    ]
    # Inline scripts without async/defer are render-blocking candidates.
    if len(render_blocking) >= 4:
        findings.append(
            FindingDraft(
                rule_id="PERF_RENDER_BLOCKING_SCRIPTS",
                title=f"{len(render_blocking)} local scripts without async/defer detected",
                severity="LOW",
                confidence=0.65,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    "Local scripts were observed without async/defer attributes. "
                    "Synchronous scripts block rendering. Browser measurements are "
                    "required to confirm the real impact."
                ),
                evidence=[EvidenceDraft(
                    "SCRIPT", "html", ", ".join(r.url for r in render_blocking[:10]),
                    {"count": len(render_blocking)},
                )],
            )
        )
    return findings
