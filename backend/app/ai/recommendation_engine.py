"""Deterministic recommendation engine.

Builds recommendations directly from real findings. Every recommendation
references at least one finding id. Used as the default engine in mock
mode and as the fallback whenever the AI output is invalid.
"""

from app.ai.schemas import Recommendation

# Templates keyed by finding rule_id -> (title, description, guidance).
_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "SEC_HTTPS_ABSENT": (
        "Enable HTTPS for the entire site",
        "Serve the site over HTTPS with a valid certificate and redirect all HTTP traffic.",
        "Obtain a TLS certificate (e.g. Let's Encrypt), configure the web server to "
        "redirect HTTP to HTTPS, and enable HSTS once HTTPS is stable.",
    ),
    "SEC_HSTS_MISSING": (
        "Add the Strict-Transport-Security header",
        "HSTS tells browsers to only use HTTPS for this site.",
        "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' once HTTPS is enforced.",
    ),
    "SEC_CSP_MISSING": (
        "Add a Content Security Policy header",
        "CSP mitigates XSS by controlling which scripts can execute.",
        "Start with a report-only CSP, then enforce a policy that allows only your "
        "own scripts and necessary third-party origins.",
    ),
    "SEC_XCTO_MISSING": (
        "Add X-Content-Type-Options: nosniff",
        "Prevents MIME-sniffing attacks.",
        "Add the 'X-Content-Type-Options: nosniff' response header on all responses.",
    ),
    "SEC_FRAME_PROTECTION_MISSING": (
        "Add frame protection (X-Frame-Options or CSP frame-ancestors)",
        "Reduces clickjacking risk.",
        "Add 'X-Frame-Options: DENY' or 'Content-Security-Policy: frame-ancestors 'self''.",
    ),
    "SEC_MIXED_CONTENT": (
        "Eliminate mixed content (HTTP resources on HTTPS pages)",
        "Mixed content is blocked by browsers and weakens transport security.",
        "Update resource URLs to HTTPS, or use protocol-relative URLs.",
    ),
    "SEC_COOKIE_MISSING_SECURE": (
        "Mark cookies as Secure",
        "Prevents cookies from being sent over plain HTTP.",
        "Set the Secure attribute on all cookies.",
    ),
    "SEC_TECH_DISCLOSURE": (
        "Remove X-Powered-By header",
        "Reduces information disclosure to attackers.",
        "Disable the X-Powered-By header in the framework/server configuration.",
    ),
    "PERF_LARGE_IMAGE": (
        "Compress and resize oversized images",
        "Large images are the most common cause of slow loads on content sites.",
        "Serve images at display size in WebP/AVIF with proper compression.",
    ),
    "PERF_HUGE_RESOURCE": (
        "Reduce very large resources",
        "Large files directly increase load time and data costs.",
        "Compress, minify, or split the resource; consider lazy loading.",
    ),
    "PERF_MANY_THIRD_PARTY_REQUESTS": (
        "Reduce third-party requests",
        "Third-party scripts block rendering and add uncontrolled latency.",
        "Audit each third-party script, load non-critical ones asynchronously or remove them.",
    ),
    "PERF_RENDER_BLOCKING_SCRIPTS": (
        "Defer non-critical JavaScript",
        "Synchronous scripts block first paint.",
        "Add async/defer attributes or use dynamic imports.",
    ),
    "PERF_LARGE_JS": (
        "Split or defer large JavaScript bundles",
        "Large bundles increase parse and execute time.",
        "Use code splitting, tree shaking, and defer loading.",
    ),
    "PERF_LARGE_HTML": (
        "Reduce HTML payload size",
        "Large HTML slows parsing and rendering.",
        "Remove unused markup, inline critical CSS, and use server-side rendering caching.",
    ),
    "PERF_IMAGES_NO_DIMENSIONS": (
        "Add width/height to images",
        "Prevents layout shift during load.",
        "Set explicit dimensions or CSS aspect-ratio on images.",
    ),
    "A11Y_IMG_MISSING_ALT": (
        "Add alt text to images",
        "Screen reader users depend on alt text; images without it are invisible.",
        "Add descriptive alt text, or alt=\"\" for decorative images.",
    ),
    "A11Y_FORM_FIELD_NO_LABEL": (
        "Associate labels with form fields",
        "Unlabeled inputs are unusable for assistive technology.",
        "Use <label for=\"...\"> or aria-label on every input, select and textarea.",
    ),
    "A11Y_HEADING_ORDER": (
        "Fix heading hierarchy",
        "Logical heading order helps all users and SEO.",
        "Ensure headings do not skip levels (h1 → h2 → h3).",
    ),
    "A11Y_HTML_LANG_MISSING": (
        "Declare the document language",
        "Screen readers need the lang attribute for correct pronunciation.",
        "Add lang=\"...\" to the <html> element.",
    ),
    "A11Y_EMPTY_LINK": (
        "Give links accessible names",
        "Links with no text are unusable for screen readers.",
        "Add visible text or aria-label to all links.",
    ),
    "A11Y_EMPTY_BUTTON": (
        "Give buttons accessible names",
        "Buttons need a name to be identified.",
        "Add text content or aria-label to buttons.",
    ),
    "PRIV_PRIVACY_POLICY_MISSING": (
        "Add a privacy policy page and link it",
        "Visitors expect to find a privacy policy; regulations often require it.",
        "Publish a privacy policy and link it from the footer and consent UI.",
    ),
    "SEO_TITLE_MISSING": (
        "Add unique page titles",
        "Titles are the strongest on-page SEO signal.",
        "Add a unique <title> to every page.",
    ),
    "SEO_META_DESCRIPTION_MISSING": (
        "Add meta descriptions",
        "Meta descriptions control SERP snippets.",
        "Write a 120-160 character meta description per page.",
    ),
    "SEO_STRUCTURED_DATA_MISSING": (
        "Add structured data (JSON-LD)",
        "Structured data enables rich results.",
        "Add Organization/Product/FAQ schema as JSON-LD.",
    ),
    "SEO_BROKEN_PAGES": (
        "Fix pages returning errors",
        "Broken pages waste crawl budget and frustrate users.",
        "Fix the URLs or return proper 301 redirects.",
    ),
    "SEO_DUPLICATE_TITLES": (
        "Make page titles unique",
        "Duplicate titles dilute search relevance.",
        "Give each page a distinct title.",
    ),
    "CONTENT_THIN": (
        "Expand thin content pages",
        "Pages with little text provide limited value.",
        "Add meaningful, unique content to thin pages.",
    ),
    "UX_NO_VIEWPORT": (
        "Add the mobile viewport meta tag",
        "Without it, mobile users get a desktop page.",
        "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
    ),
    "UX_MULTIPLE_H1": (
        "Use a single H1 per page",
        "Multiple H1s confuse the page purpose.",
        "Keep one H1 and structure the rest with h2/h3.",
    ),
    "SEC_TLS_CERT_INVALID": (
        "Fix the TLS certificate",
        "Users see browser warnings when the certificate is invalid.",
        "Renew or replace the certificate; ensure the chain is complete.",
    ),
}

_DEFAULT_GUIDANCE = (
    "Review the finding evidence and address the underlying issue. "
    "Re-run a scan to measure the improvement."
)


def generate_recommendations(
    findings: list[dict],
    evidence_by_finding: dict[int, list[dict]],
) -> list[Recommendation]:
    """Deterministic recommendations from real findings."""
    recs: list[Recommendation] = []
    by_rule: dict[str, list[dict]] = {}
    for f in findings:
        by_rule.setdefault(f.get("rule_id", ""), []).append(f)

    for rule_id, group in by_rule.items():
        primary = max(group, key=lambda f: _severity_weight(f.get("severity")))
        template = _TEMPLATES.get(rule_id)
        category = primary.get("category", "PERFORMANCE")
        if template:
            title, description, guidance = template
        else:
            title = f"Address {category.lower()} issue: {primary.get('title', '')}"
            description = (
                primary.get("description")
                or "Issue detected by automated analysis. Requires human review."
            )
            guidance = _DEFAULT_GUIDANCE
        recs.append(
            Recommendation(
                title=title,
                description=description[:1000],
                category=category,
                priority=_bucket(primary.get("severity"), primary.get("impact")),
                impact=primary.get("impact", "MEDIUM"),
                effort=primary.get("effort", "MEDIUM"),
                confidence=primary.get("confidence", 0.5),
                root_cause=primary.get("title", ""),
                finding_ids=[f["id"] for f in group[:10]],
                implementation_guidance=guidance,
            )
        )

    # Sort by severity order (P0 first).
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    recs.sort(key=lambda r: order.get(_severity_of(r), 5))
    return recs[:12]


def _severity_weight(severity: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(severity, 0)


def _severity_of(rec: Recommendation) -> str:
    impact_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
    return impact_map.get(rec.impact, "LOW")


def _bucket(severity: str, impact: str) -> str:
    sev = _severity_weight(severity)
    imp = _severity_weight(impact)
    combined = sev + imp
    if combined >= 6:
        return "P0"
    if combined >= 4:
        return "P1"
    if combined >= 2:
        return "P2"
    return "P3"
