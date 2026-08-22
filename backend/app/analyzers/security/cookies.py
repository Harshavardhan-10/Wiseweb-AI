"""Cookie security checks (observable from response Set-Cookie headers)."""

from app.analyzers.base import EvidenceDraft, FindingDraft


def check_cookies(cookies: list[dict], base_url: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    if not cookies:
        return findings

    insecure = [c for c in cookies if not c.get("secure")]
    if insecure:
        names = ", ".join(c["name"] for c in insecure[:8])
        findings.append(
            FindingDraft(
                rule_id="SEC_COOKIE_MISSING_SECURE",
                title="Cookies set without the Secure attribute",
                severity="MEDIUM",
                confidence=0.95,
                impact="MEDIUM",
                effort="LOW",
                description=(
                    f"{len(insecure)} cookie(s) lack the Secure attribute: {names}. "
                    "They can be transmitted over plain HTTP."
                ),
                evidence=[
                    EvidenceDraft(
                        evidence_type="COOKIE", source=base_url,
                        value=names[:500],
                        metadata={"count": len(insecure), "cookies": insecure[:8]},
                    )
                ],
            )
        )

    no_httponly = [c for c in cookies if not c.get("httponly")]
    if no_httponly:
        names = ", ".join(c["name"] for c in no_httponly[:8])
        findings.append(
            FindingDraft(
                rule_id="SEC_COOKIE_MISSING_HTTPONLY",
                title="Cookies without the HttpOnly attribute",
                severity="LOW",
                confidence=0.9,
                impact="LOW",
                effort="LOW",
                description=(
                    f"{len(no_httponly)} cookie(s) are readable by JavaScript: {names}."
                ),
                evidence=[
                    EvidenceDraft(
                        evidence_type="COOKIE", source=base_url,
                        value=names[:500],
                        metadata={"count": len(no_httponly), "cookies": no_httponly[:8]},
                    )
                ],
            )
        )
    return findings
