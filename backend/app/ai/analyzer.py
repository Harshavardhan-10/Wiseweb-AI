"""AI pipeline core: prompt loading, provider calls, validation, fallbacks.

The pipeline NEVER stores unvalidated AI output. Every response is parsed
as JSON and validated against the Pydantic schemas in app.ai.schemas.
When the AI is unavailable, disabled, or returns invalid data, deterministic
fallbacks (which reason over the same evidence) are used instead.
"""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from app.ai.evidence_context import EvidenceContextBuilder
from app.ai.provider import AIProvider, get_provider
from app.ai.schemas import (
    CompetitorOutput, RecommendationOutput, RootCause, RootCauseOutput,
    SummaryItem,
)
from app.config.settings import settings

logger = logging.getLogger("wisewebai.ai.pipeline")

PROMPTS_DIR = Path(__file__).parent / "prompts"
_PROMPT_CACHE: dict[str, str] = {}


def load_prompt(name: str) -> str:
    if name not in _PROMPT_CACHE:
        _PROMPT_CACHE[name] = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    return _PROMPT_CACHE[name]


def _parse_json(text: str) -> dict:
    """Parse AI output as JSON, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                raise ValueError("AI response is not valid JSON") from None
        else:
            raise ValueError("AI response is not valid JSON") from None
    if not isinstance(data, dict):
        raise ValueError("AI response is not an object")
    return data


class AiPipeline:
    def __init__(self, provider: AIProvider | None = None):
        self.provider = provider or get_provider()
        self.builder = EvidenceContextBuilder()

    @property
    def enabled(self) -> bool:
        return settings.ai_enabled and self.provider.available()

    async def root_causes(self, findings: list[dict], evidence_by_finding: dict[int, list[dict]]) -> RootCauseOutput:
        fallback = self._deterministic_root_causes(findings, evidence_by_finding)
        if not self.enabled or not findings:
            return fallback
        context = self.builder.build(findings, evidence_by_finding)
        try:
            raw = await self.provider.complete(load_prompt("root_cause.txt"), context)
            parsed = _parse_json(raw)
            output = RootCauseOutput.model_validate(parsed)
            if not output.root_causes:
                return fallback
            return output
        except (ValueError, ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("root cause AI failed, using deterministic fallback: %s", exc)
            return fallback

    async def recommendations(
        self,
        findings: list[dict],
        evidence_by_finding: dict[int, list[dict]],
        root_causes: RootCauseOutput,
    ) -> RecommendationOutput:
        fallback = self._deterministic_recommendations(findings, evidence_by_finding)
        if not self.enabled or not findings:
            return fallback
        context = {
            "findings": findings[:60],
            "evidence": {
                str(fid): ev[:5] for fid, ev in evidence_by_finding.items()
            },
            "root_causes": [r.model_dump() for r in root_causes.root_causes],
        }
        prompt = load_prompt("recommendations.txt")
        try:
            raw = await self.provider.complete(
                prompt, json.dumps(context, default=str)[: settings.ai_max_context_chars]
            )
            parsed = _parse_json(raw)
            output = RecommendationOutput.model_validate(parsed)
            if not output.recommendations:
                return fallback
            return output
        except (ValueError, ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("recommendation AI failed, using deterministic fallback: %s", exc)
            return fallback

    async def summary(
        self,
        scores: dict,
        findings: list[dict],
        recommendations: list[dict],
        metrics: dict | None = None,
    ) -> SummaryItem:
        fallback = self._deterministic_summary(scores, findings, recommendations)
        if not self.enabled:
            return fallback
        context = self.builder.build_for_summary(scores, findings, recommendations, metrics)
        try:
            raw = await self.provider.complete(load_prompt("summary.txt"), context)
            parsed = _parse_json(raw)
            item = SummaryItem.model_validate(parsed)
            if not item.executive_summary:
                return fallback
            return item
        except (ValueError, ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("summary AI failed, using deterministic fallback: %s", exc)
            return fallback

    async def competitor_analysis(
        self, self_scores: dict[str, float | None], competitor_scores: dict[str, float | None]
    ) -> CompetitorOutput:
        if not self.enabled:
            return self._deterministic_competitor(self_scores, competitor_scores)
        payload = {"you": self_scores, "competitor": competitor_scores}
        try:
            raw = await self.provider.complete(
                load_prompt("competitor.txt"),
                json.dumps(payload, default=str),
            )
            parsed = _parse_json(raw)
            output = CompetitorOutput.model_validate(parsed)
            if not output.gaps and not output.explanation and not output.summary:
                # Provider returned nothing usable (e.g. mock provider):
                # fall back to the deterministic comparison.
                return self._deterministic_competitor(self_scores, competitor_scores)
            return output
        except (ValueError, ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("competitor AI failed, using deterministic fallback: %s", exc)
            return self._deterministic_competitor(self_scores, competitor_scores)

    async def change_explanation(
        self, before: dict, after: dict, changes: list[dict]
    ) -> str:
        payload = {
            "before": {"scores": before.get("scores"), "findings": before.get("findings")},
            "after": {"scores": after.get("scores"), "findings": after.get("findings")},
            "changes": changes[:50],
        }
        if not self.enabled:
            return self._deterministic_changes(payload)
        try:
            raw = await self.provider.complete(
                load_prompt("changes.txt"), json.dumps(payload, default=str)
            )
            return raw.strip()[:3000]
        except Exception as exc:  # noqa: BLE001
            logger.warning("change AI failed, using deterministic fallback: %s", exc)
            return self._deterministic_changes(payload)

    # ------------------------------------------------------------------
    # Deterministic fallbacks (grounded in the same evidence)
    # ------------------------------------------------------------------

    @staticmethod
    def _deterministic_root_causes(findings: list[dict], evidence_by_finding: dict[int, list[dict]]) -> RootCauseOutput:
        # Group findings that share an evidence source/domain.
        groups: dict[str, dict] = {}
        for f in findings[:60]:
            domain = None
            for ev in evidence_by_finding.get(f["id"], []):
                source = ev.get("source") or ""
                if ev.get("evidence_type") in ("URL", "RESOURCE", "SCRIPT") and source:
                    domain = source.split("/")[2] if "//" in source else source
                    break
            key = f"{f.get('category')}:{domain or 'general'}"
            if key not in groups:
                groups[key] = {"title": f"{f.get('category', '').title()} issues", "ids": []}
            groups[key]["ids"].append(f.get("rule_id") or f["id"])

        root_causes = [
            RootCause(
                title=g["title"],
                description=(
                    f"Correlated {len(g['ids'])} finding(s) sharing the same "
                    "category/evidence source. Requires human review."
                ),
                affected_findings=g["ids"][:10],
                confidence=0.6,
                evidence_ids=g["ids"][:10],
            )
            for g in groups.values()
        ]
        return RootCauseOutput(root_causes=root_causes)

    @staticmethod
    def _deterministic_recommendations(findings: list[dict], evidence_by_finding: dict[int, list[dict]]) -> RecommendationOutput:
        from app.ai.recommendation_engine import generate_recommendations
        recs = generate_recommendations(findings, evidence_by_finding)
        return RecommendationOutput(recommendations=[rec.model_dump() for rec in recs])  # type: ignore[arg-type]

    @staticmethod
    def _deterministic_summary(scores: dict, findings: list[dict], recommendations: list[dict]) -> SummaryItem:
        overall = scores.get("overall")
        categories = scores.get("categories", {})
        worst = sorted(
            ((k, v) for k, v in categories.items() if v is not None),
            key=lambda kv: kv[1],
        )
        risks = [
            f["title"] for f in findings
            if f.get("severity") in ("CRITICAL", "HIGH")
        ][:4]
        opportunities = [
            rec.get("title") for rec in recommendations[:3]
            if rec.get("impact") in ("HIGH", "MEDIUM")
        ]
        headline = (
            f"Overall health score is {overall:.0f}/100."
            if overall is not None
            else "Overall health score could not be computed yet."
        )
        worst_text = ", ".join(f"{k} {v:.0f}" for k, v in worst[:3]) or "all categories unmeasured"
        summary_text = (
            f"Health score {overall:.0f}/100. Weakest areas: {worst_text}. "
            f"{len(risks)} critical/high issues identified. "
            f"Highest-impact next steps: {', '.join(opportunities[:2]) or 'none recorded'}."
        )
        return SummaryItem(
            headline=headline,
            executive_summary=summary_text,
            top_risks=risks or ["No critical or high findings recorded."],
            biggest_opportunities=opportunities or ["Not enough measured data to prioritize."],
            roadmap=[f"{i+1}. {r}" for i, r in enumerate([rec.get("title") for rec in recommendations[:5]])] or [],
        )

    @staticmethod
    def _deterministic_competitor(self_scores: dict, competitor_scores: dict) -> CompetitorOutput:
        from app.ai.schemas import CompetitorGap
        gaps = []
        dims = ["SECURITY", "PERFORMANCE", "ACCESSIBILITY", "PRIVACY", "SEO", "CONTENT", "UX", "ARCHITECTURE"]
        for dim in dims:
            you = self_scores.get(dim)
            comp = competitor_scores.get(dim)
            if you is None or comp is None:
                continue
            gap = round(you - comp, 1)
            gaps.append(CompetitorGap(dimension=dim, you=you, competitor=comp, gap=gap,
                                      explanation=_gap_text(dim, gap)))
        behind = [g for g in gaps if g.gap < -1]
        ahead = [g for g in gaps if g.gap > 1]
        explanation = (
            "Deterministic comparison (AI disabled). "
            f"Behind on: {', '.join(g.dimension for g in behind[:3]) or 'nothing'} — "
            f"ahead on: {', '.join(g.dimension for g in ahead[:3]) or 'nothing'}."
        )
        first = min(gaps, key=lambda g: g.gap) if gaps else None
        summary = (
            f"Improve {first.dimension} first (gap {first.gap:.0f} points)."
            if first
            else "Insufficient measured data to compare."
        )
        return CompetitorOutput(gaps=gaps, explanation=explanation, summary=summary)

    @staticmethod
    def _deterministic_changes(payload: dict) -> str:
        before = payload.get("before", {}).get("scores", {}) or {}
        after = payload.get("after", {}).get("scores", {}) or {}
        changes = payload.get("changes", [])
        lines = ["Change summary (deterministic):"]
        for key in ["overall", "SECURITY", "PERFORMANCE", "ACCESSIBILITY", "PRIVACY", "SEO"]:
            b, a = before.get(key), after.get(key)
            if b is None or a is None:
                continue
            delta = a - b
            arrow = "improved" if delta > 0 else "worsened" if delta < 0 else "unchanged"
            lines.append(f"  {key}: {b:.0f} -> {a:.0f} ({arrow} by {abs(delta):.0f}).")
        for ch in changes[:10]:
            lines.append(f"  [{ch.get('type')}] {ch.get('category')}: {ch.get('label')}")
        return "\n".join(lines)


def _gap_text(dim: str, gap: float) -> str:
    if gap < 0:
        return f"{dim} is {abs(gap):.0f} points behind the competitor."
    if gap > 0:
        return f"{dim} is {gap:.0f} points ahead of the competitor."
    return f"{dim} is level with the competitor."
