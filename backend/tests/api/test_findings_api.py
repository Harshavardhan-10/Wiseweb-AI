"""API tests: findings listing + status updates."""

from datetime import datetime, timezone

from app.models.finding import Finding
from app.models.scan import Scan


def _seed_scan_and_finding(client, db, auth_headers):
    website = client.post("/api/v1/websites", json={
        "name": "Example Inc", "url": "https://example.com",
    }, headers=auth_headers).json()
    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]

    scan = Scan(
        website_id=website["id"], status="COMPLETED", stage="COMPLETED",
        progress_percent=100, crawl_depth=2, page_limit=10,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()
    finding = Finding(
        scan_id=scan.id, category="SECURITY", rule_id="SEC_HSTS_MISSING",
        title="HSTS header missing", severity="MEDIUM", confidence=0.9,
        impact="MEDIUM", effort="LOW", affected_url="https://example.com/",
    )
    db.add(finding)
    db.commit()
    db.refresh(scan)
    db.refresh(finding)
    return scan.id, finding.id


def test_list_findings_for_scan(client, db, auth_headers):
    scan_id, _ = _seed_scan_and_finding(client, db, auth_headers)
    response = client.get(f"/api/v1/findings/scan/{scan_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    item = response.json()["items"][0]
    assert item["rule_id"] == "SEC_HSTS_MISSING"
    assert item["severity"] == "MEDIUM"


def test_filter_findings_by_severity(client, db, auth_headers):
    scan_id, _ = _seed_scan_and_finding(client, db, auth_headers)
    response = client.get(
        f"/api/v1/findings/scan/{scan_id}?severity=HIGH", headers=auth_headers
    )
    assert response.json()["total"] == 0


def test_get_single_finding(client, db, auth_headers):
    _, finding_id = _seed_scan_and_finding(client, db, auth_headers)
    response = client.get(f"/api/v1/findings/{finding_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == finding_id


def test_update_finding_status(client, db, auth_headers):
    _, finding_id = _seed_scan_and_finding(client, db, auth_headers)
    response = client.patch(
        f"/api/v1/findings/{finding_id}", json={"status": "FIXED"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "FIXED"


def test_update_finding_invalid_status_is_validation_error(client, db, auth_headers):
    _, finding_id = _seed_scan_and_finding(client, db, auth_headers)
    response = client.patch(
        f"/api/v1/findings/{finding_id}", json={"status": "NOT_A_STATUS"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_findings_not_accessible_by_other_users(client, db, auth_headers):
    _, finding_id = _seed_scan_and_finding(client, db, auth_headers)
    second = client.post("/api/v1/auth/register", json={
        "email": "intruder@example.com", "password": "strongpass123", "full_name": "Intruder",
    }).json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get(f"/api/v1/findings/{finding_id}", headers=headers).status_code == 404
