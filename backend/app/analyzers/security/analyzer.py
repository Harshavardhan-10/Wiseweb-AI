"""Security analyzer: passive, deterministic security posture analysis.

Checks (each rule independent):
- HTTPS, HSTS, CSP, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy, frame protection
- cookie security attributes
- mixed content (http resources on https pages)
- technology disclosure
- observable exposure signals (from crawled data only)
- TLS certificate validity observation (normal validation)
"""

import logging

from app.analyzers.base import AnalyzerResult, BaseAnalyzer, ScanContext, EvidenceDraft, FindingDraft
from app.analyzers.registry import AnalyzerRegistry
from app.analyzers.security.cookies import check_cookies
from app.analyzers.security.exposure import check_observable_endpoints
from app.analyzers.security.headers import (
    check_csp, check_frame_protection, check_hsts, check_https,
    check_permissions_policy, check_referrer_policy, check_technology_disclosure,
    check_x_content_type_options,
)

logger = logging.getLogger("wisewebai.analyzers.security")


class SecurityAnalyzer(BaseAnalyzer):
    name = "security"
    category = "SECURITY"

    async def analyze(self, context: ScanContext) -> AnalyzerResult:
        result = AnalyzerResult()
        home = context.home_page
        if not home:
            result.status = "FAILED"
            result.error = "No pages crawled; security analysis requires at least one page."
            return result

        headers = home.headers
        base_url = context.base_url

        # Header checks
        result.findings += check_https(headers, base_url)
        result.findings += check_hsts(headers)
        result.findings += check_csp(headers)
        result.findings += check_x_content_type_options(headers)
        result.findings += check_referrer_policy(headers)
        result.findings += check_permissions_policy(headers)
        result.findings += check_frame_protection(headers)
        result.findings += check_technology_disclosure(headers)

        # Cookie checks
        result.findings += check_cookies(home.cookies, base_url)

        # Mixed content
        result.findings += self._check_mixed_content(context)

        # Exposure (observable only)
        htmls = [p.html for p in context.pages if p.html]
        result.findings += check_observable_endpoints(htmls, base_url)

        # TLS observation (best-effort)
        tls_finding = await self._observe_tls_finding(context)
        if tls_finding:
            result.findings.append(tls_finding)

        for f in result.findings:
            f.category = self.category
        return result

    def _check_mixed_content(self, context: ScanContext) -> list[FindingDraft]:
        findings: list[FindingDraft] = []
        https_home = context.base_url.startswith("https://")
        if not https_home:
            return findings
        http_resources = [
            r for r in context.resources
            if r.url.startswith("http://") and not r.url.startswith("http://localhost")
        ]
        if http_resources:
            urls = ", ".join(r.url for r in http_resources[:10])
            findings.append(
                FindingDraft(
                    rule_id="SEC_MIXED_CONTENT",
                    title="Mixed content: HTTP resources loaded by an HTTPS page",
                    severity="HIGH",
                    confidence=0.95,
                    impact="HIGH",
                    effort="MEDIUM",
                    description=(
                        f"{len(http_resources)} resource(s) are loaded over plain HTTP "
                        "from an HTTPS page. Browsers block or warn on mixed content, "
                        "and it weakens transport security."
                    ),
                    evidence=[EvidenceDraft("URL", context.base_url, urls[:1000],
                                             {"count": len(http_resources)})],
                )
            )
        return findings

    async def _observe_tls_finding(self, context: ScanContext) -> FindingDraft | None:
        from urllib.parse import urlparse

        from app.analyzers.security.tls import observe_tls

        parsed = urlparse(context.base_url)
        hostname = parsed.hostname
        if not hostname or parsed.scheme != "https":
            return None
        observation = await observe_tls(hostname)
        if not observation.valid_certificate:
            return FindingDraft(
                rule_id="SEC_TLS_CERT_INVALID",
                title="TLS certificate could not be verified",
                severity="HIGH",
                confidence=0.9,
                impact="HIGH",
                effort="LOW",
                description=(
                    "A standard TLS handshake could not validate the certificate "
                    f"chain ({observation.error or 'unknown reason'}). Users may see "
                    "browser warnings."
                ),
                affected_url=context.base_url,
                evidence=[EvidenceDraft("CERTIFICATE", hostname, observation.error or "validation failed")],
            )
        return None


AnalyzerRegistry.register(SecurityAnalyzer)
