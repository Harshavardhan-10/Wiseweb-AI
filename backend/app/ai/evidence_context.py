"""EvidenceContextBuilder.

The AI never sees raw HTML. It receives a compact, structured context of
findings + evidence built here. Responsibilities:
- collect relevant findings
- collect supporting evidence
- remove duplicates
- limit context size (configurable)
- format structured AI context
"""

import json
import logging
from typing import Any

from app.config.settings import settings

logger = logging.getLogger("wisewebai.ai.evidence")


class EvidenceContextBuilder:
    def __init__(self, max_chars: int | None = None):
        self.max_chars = max_chars or settings.ai_max_context_chars

    def build(
        self,
        findings: list[dict],
        evidence_by_finding: dict[int, list[dict]],
        metrics: dict[str, Any] | None = None,
    ) -> str:
        """Serialize findings + evidence into a compact JSON context."""
        sections: dict[str, Any] = {
            "metrics": metrics or {},
            "findings": [],
        }

        for f in findings[:80]:
            entry = {
                "id": f["id"],
                "rule_id": f["rule_id"],
                "category": f["category"],
                "title": f["title"],
                "description": (f.get("description") or "")[:300],
                "severity": f["severity"],
                "impact": f["impact"],
                "effort": f["effort"],
                "confidence": f["confidence"],
                "affected_url": f.get("affected_url"),
            }
            evs = evidence_by_finding.get(f["id"], [])
            entry["evidence"] = [
                {
                    "type": e.get("evidence_type"),
                    "source": (e.get("source") or "")[:150],
                    "value": (e.get("value") or "")[:200],
                }
                for e in evs[:6]
            ]
            sections["findings"].append(entry)

        text = json.dumps(sections, ensure_ascii=False, indent=0, default=str)
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + "\n[context truncated]"
        return text

    def build_for_summary(
        self,
        scores: dict[str, Any],
        findings_summary: list[dict],
        recommendations: list[dict],
        metrics: dict[str, Any] | None = None,
    ) -> str:
        payload = {
            "scores": scores,
            "metrics": metrics or {},
            "critical_high_findings": findings_summary[:25],
            "top_recommendations": recommendations[:15],
        }
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) > self.max_chars:
            text = text[: self.max_chars] + "\n[context truncated]"
        return text
