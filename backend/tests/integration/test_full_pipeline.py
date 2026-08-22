"""End-to-end scan pipeline test against the bundled demo site.

Runs the full ScanOrchestrator (crawl -> analyzers -> scoring -> AI phase)
against the real demo-site/ pages with the DEMO-ONLY allow_internal flag.
"""

import os
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

from app.core.database import init_db
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.page import Page
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.scan import Scan
from app.models.scan_comparison import ScanSummary
from app.models.technology import Technology
from app.models.user import User
from app.workers.orchestrator import ScanOrchestrator

DEMO_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..", "demo-site",
)


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DEMO_SITE, **kwargs)

    def log_message(self, fmt, *args):  # noqa: ARG002
        pass


@pytest.fixture(scope="module")
def demo_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_full_scan_pipeline(db, demo_server):
    init_db()
    user = User(
        email="integration@example.com", password_hash="x", full_name="Integration",
        is_active=True,
    )
    db.add(user)
    db.flush()

    from app.models.website import Website
    website = Website(
        user_id=user.id, name="Demo Integration", url=demo_server,
        normalized_url=demo_server + "/", website_type="ecommerce",
        industry="Retail",
    )
    db.add(website)
    db.flush()

    scan = Scan(
        website_id=website.id, status="QUEUED", stage="QUEUED", progress_percent=0,
        crawl_depth=2, page_limit=20, started_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.commit()
    scan_id = scan.id

    # DEMO ONLY: allow_internal is the documented demo escape hatch.
    completed = ScanOrchestrator(db, allow_internal=True).run(scan_id)
    assert completed.status == "COMPLETED", completed.error_message

    pages = db.scalars(select(Page).where(Page.scan_id == scan_id)).all()
    assert len(pages) >= 4, f"expected demo pages, got {[p.url for p in pages]}"

    resources = db.scalars(select(Resource).where(Resource.scan_id == scan_id)).all()
    assert resources, "expected resources"

    technologies = db.scalars(select(Technology).where(Technology.scan_id == scan_id)).all()
    assert technologies, "expected technology detections"

    findings = db.scalars(select(Finding).where(Finding.scan_id == scan_id)).all()
    assert findings, "expected findings"
    categories = {f.category for f in findings}
    assert "SECURITY" in categories and "SEO" in categories

    evidence = db.scalars(select(Evidence).where(Evidence.finding_id.in_([f.id for f in findings]))).all()
    assert evidence, "every finding must carry evidence"

    recommendations = db.scalars(select(Recommendation).where(Recommendation.scan_id == scan_id)).all()
    assert recommendations, "expected recommendations"
    for rec in recommendations:
        assert rec.priority in ("P0", "P1", "P2", "P3")

    summary = db.scalar(select(ScanSummary).where(ScanSummary.scan_id == scan_id))
    assert summary is not None
    assert summary.headline

    db.refresh(completed)
    assert completed.overall_score is not None
    assert completed.security_score is not None
    assert completed.analyzer_status is not None
    assert all(status == "COMPLETED" for status in completed.analyzer_status.values()), completed.analyzer_status
