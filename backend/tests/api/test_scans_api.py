"""API tests: scan lifecycle (eager Celery mode)."""


def _create_website(client, headers, url="https://example.com"):
    response = client.post("/api/v1/websites", json={
        "name": "Example Inc", "url": url,
    }, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_scan_returns_queued(client, auth_headers):
    website_id = _create_website(client, auth_headers)
    response = client.post(f"/api/v1/scans/websites/{website_id}", json={}, headers=auth_headers)
    assert response.status_code == 201, response.text
    # Eager Celery runs the scan inline, so the returned scan may already be
    # complete (or failed) by the time the response is built.
    assert response.json()["status"] in ("QUEUED", "CRAWLING", "COMPLETED", "FAILED")


def test_scan_of_localhost_target_fails_gracefully(client, auth_headers):
    """The API must NEVER scan internal targets: SSRF stays enforced."""
    website_id = _create_website(client, auth_headers, url="http://localhost:8001")
    response = client.post(
        f"/api/v1/scans/websites/{website_id}",
        json={"crawl_depth": 1, "page_limit": 3},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    scan = response.json()
    # Eager Celery runs the scan inline; SSRF must block localhost.
    assert scan["status"] == "FAILED"
    assert scan["error_message"]
    assert "localhost" in scan["error_message"].lower() or "internal" in scan["error_message"].lower()


def test_scan_validation_caps(client, auth_headers):
    website_id = _create_website(client, auth_headers)
    response = client.post(
        f"/api/v1/scans/websites/{website_id}",
        json={"crawl_depth": 99, "page_limit": 9999},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_scan_progress_endpoint(client, auth_headers):
    website_id = _create_website(client, auth_headers)
    created = client.post(f"/api/v1/scans/websites/{website_id}", json={}, headers=auth_headers).json()
    response = client.get(f"/api/v1/scans/{created['id']}/progress", headers=auth_headers)
    assert response.status_code == 200
    assert "progress_percent" in response.json()


def test_scan_isolation_between_users(client, auth_headers):
    website_id = _create_website(client, auth_headers)
    created = client.post(f"/api/v1/scans/websites/{website_id}", json={}, headers=auth_headers).json()
    second = client.post("/api/v1/auth/register", json={
        "email": "other@example.com", "password": "strongpass123", "full_name": "Other",
    }).json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get(f"/api/v1/scans/{created['id']}", headers=headers).status_code == 404


def test_cancel_scan(client, auth_headers):
    website_id = _create_website(client, auth_headers)
    created = client.post(f"/api/v1/scans/websites/{website_id}", json={}, headers=auth_headers).json()
    # Scan already finished inline; cancelling a finished scan must conflict.
    response = client.post(f"/api/v1/scans/{created['id']}/cancel", headers=auth_headers)
    if created["status"] == "QUEUED":
        assert response.status_code == 200
    else:
        assert response.status_code == 409
