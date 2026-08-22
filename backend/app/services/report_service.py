"""Report service: executive + developer reports.

Reports are assembled from real scan data (scores, findings, evidence,
recommendations, summary). PDF export is a documented future feature.
"""

from sqlalchemy.orm import Session

from app.ai.analyzer import AiPipeline
from app.core.exceptions import NotFoundError
from app.services.scan_service import ScanService


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.scans = ScanService(db)

    def executive_report(self, scan_id: int, user_id: int, ai_pipeline: AiPipeline | None = None) -> dict:
        scan = self.scans.get_for_user(scan_id, user_id)
        summary = scan.summary
        recommendations = sorted(
            scan.recommendations, key=lambda r: -r.priority_score
        )[:5]
        critical = [f for f in scan.findings if f.severity == "CRITICAL"][:5]
        high = [f for f in scan.findings if f.severity == "HIGH"][:8]

        return {
            "website": {"name": scan.website.name, "url": scan.website.url},
            "scan": {"id": scan.id, "status": scan.status, "completed_at": scan.completed_at},
            "overall_score": scan.overall_score,
            "scores": {
                "SECURITY": scan.security_score, "PERFORMANCE": scan.performance_score,
                "ACCESSIBILITY": scan.accessibility_score, "PRIVACY": scan.privacy_score,
                "SEO": scan.seo_score, "CONTENT": scan.content_score,
                "UX": scan.ux_score, "ARCHITECTURE": scan.architecture_score,
            },
            "summary": {
                "headline": summary.headline if summary else None,
                "executive_summary": summary.executive_summary if summary else None,
                "top_risks": summary.top_risks if summary else [],
                "biggest_opportunities": summary.biggest_opportunities if summary else [],
                "roadmap": summary.roadmap if summary else [],
            },
            "top_risks": [{"title": f.title, "severity": f.severity} for f in critical + high],
            "top_recommendations": [
                {
                    "title": r.title, "priority": r.priority, "impact": r.impact,
                    "effort": r.effort, "confidence": r.confidence,
                }
                for r in recommendations
            ],
        }

    def developer_report(self, scan_id: int, user_id: int) -> dict:
        scan = self.scans.get_for_user(scan_id, user_id)
        findings = []
        for f in sorted(scan.findings, key=lambda x: (x.severity != "INFO", x.severity)):
            findings.append({
                "id": f.id, "category": f.category, "rule_id": f.rule_id,
                "title": f.title, "severity": f.severity, "confidence": f.confidence,
                "impact": f.impact, "effort": f.effort, "affected_url": f.affected_url,
                "description": f.description,
                "evidence": [
                    {"type": e.evidence_type, "source": e.source, "value": e.value}
                    for e in f.evidence
                ],
            })
        return {
            "website": {"name": scan.website.name, "url": scan.website.url},
            "scan": {"id": scan.id, "status": scan.status},
            "findings_count": len(findings),
            "findings": findings,
            "technologies": [
                {"name": t.name, "category": t.category, "confidence": t.confidence}
                for t in scan.technologies
            ],
            "metrics": {
                "pages_discovered": scan.pages_discovered,
                "pages_analyzed": scan.pages_analyzed,
            },
        }
