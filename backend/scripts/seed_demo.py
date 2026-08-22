"""Seed demo data: demo user + demo website + optional demo scan.

Demo data is clearly marked:
- the user email is demo@wiseweb-ai.local
- the website is named "Acme Widgets (Demo)"
- the scan runs against the bundled local demo site with SSRF checks
  relaxed ONLY for this demo path (loud warning is logged).

Usage (from backend/):
  python -m scripts.seed_demo            # user + website only
  python -m scripts.seed_demo --scan     # also run a full demo scan
"""

import argparse
import logging

from app.config.settings import settings
from app.core.database import SessionLocal, init_db
from app.services.auth_service import AuthService
from app.services.scan_service import ScanService
from app.services.website_service import WebsiteService
from app.utils.urls import normalize_url
from app.workers.orchestrator import ScanOrchestrator

logger = logging.getLogger("wisewebai.seed")

DEMO_URL = "http://localhost:8001"


def seed_demo_if_needed(scan: bool = False) -> dict:
    """Create the demo user/website (idempotent). Returns created ids."""
    init_db()
    db = SessionLocal()
    try:
        auth = AuthService(db)
        user = auth.users.get_by_email(settings.demo_user_email)
        if user is None:
            user = auth.register(
                settings.demo_user_email, settings.demo_user_password, "Demo User"
            )
            logger.info("created demo user %s", settings.demo_user_email)

        normalized = normalize_url(DEMO_URL)
        websites = WebsiteService(db)
        website = websites.websites.get_by_normalized_url(normalized, user.id)
        if website is None:
            website = websites.create(
                user_id=user.id,
                name="Acme Widgets (Demo)",
                url=DEMO_URL,
                website_type="ecommerce",
                industry="Retail",
                target_audience="Demo",
                description="Demo website with intentional, safe quality issues.",
            )
            logger.info("created demo website %s", DEMO_URL)

        scan_id = None
        if scan:
            scan_model = ScanService(db).create(
                website.id, user.id, crawl_depth=2, page_limit=20
            )
            # DEMO ONLY: allow_internal relaxes SSRF for the local demo site.
            logger.warning(
                "DEMO SCAN: scanning localhost demo site with relaxed SSRF (demo only)"
            )
            ScanOrchestrator(db, allow_internal=True).run(scan_model.id)
            scan_id = scan_model.id
            logger.info("demo scan %s completed status=%s", scan_id, scan_model.status)

        return {"user_id": user.id, "website_id": website.id, "scan_id": scan_id}
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Wiseweb-AI demo data")
    parser.add_argument("--scan", action="store_true", help="Also run a demo scan")
    args = parser.parse_args()
    result = seed_demo_if_needed(scan=args.scan)
    print("Demo data ready:", result)


if __name__ == "__main__":
    main()
