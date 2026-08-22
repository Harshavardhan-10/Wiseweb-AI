"""Security header checks (deterministic, passive)."""

from app.analyzers.base import EvidenceDraft, FindingDraft


def _ev(evidence_type: str, source: str, value: str, **metadata) -> EvidenceDraft:
    return EvidenceDraft(evidence_type=evidence_type, source=source, value=value[:2000], metadata=metadata)


def check_https(headers: dict[str, str], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if base_url.startswith("http://"):
        findings.append(
            FindingDraft(
                rule_id="SEC_HTTPS_ABSENT",
                title="Site is served over unencrypted HTTP",
                severity="HIGH",
                confidence=1.0,
                impact="HIGH",
                effort="LOW",
                description=(
                    "The site responds over plain HTTP. Traffic (including "
                    "credentials if any forms exist) is transmitted without encryption."
                ),
                affected_url=base_url,
                evidence=[_ev("URL", base_url, "http:// scheme observed")],
            )
        )
    return findings


def check_hsts(headers: dict[str, str]) -> list[FindingDraft]:
    value = headers.get("strict-transport-security")
    if not value:
        return [
            FindingDraft(
                rule_id="SEC_HSTS_MISSING",
                title="HTTP Strict Transport Security (HSTS) header is missing",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    "No Strict-Transport-Security header was observed. Browsers "
                    "cannot enforce HTTPS for this site, allowing downgrade attempts."
                ),
                evidence=[_ev("HTTP_HEADER", "response headers", "strict-transport-security: (absent)")],
            )
        ]
    findings: list[FindingDraft] = []
    if "includeSubDomains" not in value:
        findings.append(
            FindingDraft(
                rule_id="SEC_HSTS_NO_SUBDOMAINS",
                title="HSTS does not include subdomains",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description="The Strict-Transport-Security header does not cover subdomains.",
                evidence=[_ev("HTTP_HEADER", "strict-transport-security", value)],
            )
        )
    if "max-age=" in value:
        try:
            max_age = int(value.split("max-age=")[1].split(";")[0].strip())
            if max_age < 15552000:
                findings.append(
                    FindingDraft(
                        rule_id="SEC_HSTS_SHORT_MAXAGE",
                        title="HSTS max-age is shorter than recommended (180 days)",
                        severity="LOW",
                        confidence=0.9,
                        impact="LOW",
                        effort="LOW",
                        description="HSTS max-age below 15552000 seconds provides weaker protection.",
                        evidence=[_ev("HTTP_HEADER", "strict-transport-security", value)],
                    )
                )
        except (ValueError, IndexError):
            pass
    return findings


def check_csp(headers: dict[str, str]) -> list[FindingDraft]:
    value = headers.get("content-security-policy")
    if not value:
        return [
            FindingDraft(
                rule_id="SEC_CSP_MISSING",
                title="Content Security Policy (CSP) header is missing",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    "No Content-Security-Policy header was observed. XSS risks are "
                    "not mitigated by CSP."
                ),
                evidence=[_ev("HTTP_HEADER", "response headers", "content-security-policy: (absent)")],
            )
        ]
    findings: list[FindingDraft] = []
    lowered = value.lower()
    if "unsafe-inline" in lowered:
        findings.append(
            FindingDraft(
                rule_id="SEC_CSP_UNSAFE_INLINE",
                title="CSP allows 'unsafe-inline'",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="MEDIUM",
                description=(
                    "The Content-Security-Policy permits inline script execution, "
                    "which weakens XSS protection."
                ),
                evidence=[_ev("HTTP_HEADER", "content-security-policy", value)],
            )
        )
    if "unsafe-eval" in lowered:
        findings.append(
            FindingDraft(
                rule_id="SEC_CSP_UNSAFE_EVAL",
                title="CSP allows 'unsafe-eval'",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="MEDIUM",
                description="The Content-Security-Policy permits eval(), which reduces XSS hardening.",
                evidence=[_ev("HTTP_HEADER", "content-security-policy", value)],
            )
        )
    return findings


def check_x_content_type_options(headers: dict[str, str]) -> list[FindingDraft]:
    if headers.get("x-content-type-options") != "nosniff":
        return [
            FindingDraft(
                rule_id="SEC_XCTO_MISSING",
                title="X-Content-Type-Options header is missing or not 'nosniff'",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description="Missing X-Content-Type-Options: nosniff can allow MIME sniffing attacks.",
                evidence=[_ev("HTTP_HEADER", "response headers", "x-content-type-options: (absent)")],
            )
        ]
    return []


def check_referrer_policy(headers: dict[str, str]) -> list[FindingDraft]:
    if not headers.get("referrer-policy"):
        return [
            FindingDraft(
                rule_id="SEC_REFERRER_POLICY_MISSING",
                title="Referrer-Policy header is missing",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Referrer-Policy is not set; referrers may leak full URLs to third parties.",
                evidence=[_ev("HTTP_HEADER", "response headers", "referrer-policy: (absent)")],
            )
        ]
    return []


def check_permissions_policy(headers: dict[str, str]) -> list[FindingDraft]:
    if not headers.get("permissions-policy") and not headers.get("feature-policy"):
        return [
            FindingDraft(
                rule_id="SEC_PERMISSIONS_POLICY_MISSING",
                title="Permissions-Policy header is missing",
                severity="LOW",
                confidence=0.8,
                impact="LOW",
                effort="LOW",
                description="Permissions-Policy is not set, so browser APIs are available to all origins.",
                evidence=[_ev("HTTP_HEADER", "response headers", "permissions-policy: (absent)")],
            )
        ]
    return []


def check_frame_protection(headers: dict[str, str]) -> list[FindingDraft]:
    csp = headers.get("content-security-policy", "")
    xfo = headers.get("x-frame-options")
    if "frame-ancestors" in csp.lower():
        return []
    if not xfo:
        return [
            FindingDraft(
                rule_id="SEC_FRAME_PROTECTION_MISSING",
                title="No frame protection (X-Frame-Options / CSP frame-ancestors)",
                severity="MEDIUM",
                confidence=0.9,
                impact="MEDIUM",
                effort="LOW",
                description="The page does not declare frame protection, increasing clickjacking risk.",
                evidence=[_ev("HTTP_HEADER", "response headers", "x-frame-options: (absent); csp frame-ancestors: (absent)")],
            )
        ]
    return []


def check_technology_disclosure(headers: dict[str, str]) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    powered_by = headers.get("x-powered-by")
    if powered_by:
        findings.append(
            FindingDraft(
                rule_id="SEC_TECH_DISCLOSURE",
                title="Server technology disclosed via X-Powered-By header",
                severity="LOW",
                confidence=0.95,
                impact="LOW",
                effort="LOW",
                description=f"The X-Powered-By header reveals: {powered_by}",
                evidence=[_ev("HTTP_HEADER", "x-powered-by", powered_by)],
            )
        )
    server = headers.get("server")
    if server and server.lower() not in ("cloudflare",):
        # Server headers are common; only flag when they include version numbers.
        import re
        if re.search(r"\d+\.\d+", server):
            findings.append(
                FindingDraft(
                    rule_id="SEC_SERVER_VERSION_DISCLOSURE",
                    title="Web server version disclosed",
                    severity="LOW",
                    confidence=0.9,
                    impact="LOW",
                    effort="LOW",
                    description=f"The Server header exposes a version: {server}",
                    evidence=[_ev("HTTP_HEADER", "server", server)],
                )
            )
    return findings
