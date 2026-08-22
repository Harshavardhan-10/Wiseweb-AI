"""Script-level performance checks."""

from app.analyzers.base import EvidenceDraft, FindingDraft

LARGE_JS_BYTES = 400 * 1024
LARGE_CSS_BYTES = 200 * 1024


def check_script_sizes(resources) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    js = [r for r in resources if r.resource_type == "JS" and (r.size_bytes or 0) >= LARGE_JS_BYTES]
    js.sort(key=lambda r: -(r.size_bytes or 0))
    for r in js[:5]:
        findings.append(
            FindingDraft(
                rule_id="PERF_LARGE_JS",
                title=f"Large JavaScript file ({(r.size_bytes or 0) / 1024:.0f} KB)",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    f"Script {r.url} is {(r.size_bytes or 0) / 1024:.0f} KB. Large bundles "
                    "increase parse/execute time."
                ),
                affected_url=r.url,
                evidence=[EvidenceDraft("RESOURCE", r.url, f"size_bytes={r.size_bytes}",
                                         {"size_bytes": r.size_bytes})],
            )
        )
    css = [r for r in resources if r.resource_type == "CSS" and (r.size_bytes or 0) >= LARGE_CSS_BYTES]
    css.sort(key=lambda r: -(r.size_bytes or 0))
    for r in css[:3]:
        findings.append(
            FindingDraft(
                rule_id="PERF_LARGE_CSS",
                title=f"Large CSS file ({(r.size_bytes or 0) / 1024:.0f} KB)",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="MEDIUM",
                description=f"Stylesheet {r.url} is {(r.size_bytes or 0) / 1024:.0f} KB.",
                affected_url=r.url,
                evidence=[EvidenceDraft("RESOURCE", r.url, f"size_bytes={r.size_bytes}",
                                         {"size_bytes": r.size_bytes})],
            )
        )
    return findings
