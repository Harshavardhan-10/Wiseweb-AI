"""Monitoring / change detection between two scans of the same website."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.scan import Scan
from app.services.scan_service import ScanService


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.scans = ScanService(db)

    def compare_scans(
        self, user_id: int, base_scan_id: int, compare_scan_id: int, website_id: int
    ) -> dict:
        base = self.scans.get_for_user(base_scan_id, user_id)
        compare = self.scans.get_for_user(compare_scan_id, user_id)
        if base.website_id != website_id or compare.website_id != website_id:
            raise NotFoundError("Scans do not belong to the requested website.")
        if base.id == compare.id:
            raise ValidationError("Select two different scans to compare.")

        changes = {
            "pages": self._diff(
                {p.url for p in base.pages}, {p.url for p in compare.pages}, "pages"
            ),
            "resources": self._diff(
                {r.url for r in base.resources}, {r.url for r in compare.resources}, "resources"
            ),
            "technologies": self._diff(
                {t.name for t in base.technologies}, {t.name for t in compare.technologies}, "technologies"
            ),
            "third_party_domains": self._diff(
                {r.domain for r in base.resources if r.is_external and r.domain},
                {r.domain for r in compare.resources if r.is_external and r.domain},
                "third_party",
            ),
            "headers": self._diff_headers(base, compare),
            "scores": self._score_deltas(base, compare),
            "findings": self._finding_deltas(base, compare),
        }
        return changes

    def _diff(self, before: set, after: set, category: str) -> dict:
        return {
            "added": [{"type": "added", "category": category, "label": x} for x in sorted(after - before)],
            "removed": [{"type": "removed", "category": category, "label": x} for x in sorted(before - after)],
        }

    def _diff_headers(self, base: Scan, compare: Scan) -> dict:
        home_b = next((p for p in base.pages if p.depth == 0), None)
        home_c = next((p for p in compare.pages if p.depth == 0), None)
        b = home_b.headers if home_b else {}
        c = home_c.headers if home_c else {}
        changed = []
        for key in sorted(set(b) | set(c)):
            if b.get(key) != c.get(key):
                changed.append({
                    "type": "changed", "category": "header", "label": key,
                    "detail": f"{b.get(key, '(removed)')[:80]} -> {c.get(key, '(removed)')[:80]}",
                })
        return {"changed": changed}

    def _score_deltas(self, base: Scan, compare: Scan) -> list[dict]:
        deltas = []
        fields = [
            ("overall", "overall_score"), ("SECURITY", "security_score"),
            ("PERFORMANCE", "performance_score"), ("ACCESSIBILITY", "accessibility_score"),
            ("PRIVACY", "privacy_score"), ("SEO", "seo_score"),
            ("CONTENT", "content_score"), ("UX", "ux_score"), ("ARCHITECTURE", "architecture_score"),
        ]
        for label, field in fields:
            b = getattr(base, field)
            a = getattr(compare, field)
            if b is None or a is None:
                continue
            deltas.append({
                "label": label, "before": b, "after": a, "delta": round(a - b, 1),
            })
        return deltas

    def _finding_deltas(self, base: Scan, compare: Scan) -> dict:
        b_rules = {f.rule_id: f for f in base.findings}
        c_rules = {f.rule_id: f for f in compare.findings}
        fixed = [
            {"rule_id": rid, "title": f.title} for rid, f in b_rules.items() if rid not in c_rules
        ]
        new = [
            {"rule_id": rid, "title": f.title, "severity": f.severity}
            for rid, f in c_rules.items() if rid not in b_rules
        ]
        return {"fixed": fixed, "new": new}
