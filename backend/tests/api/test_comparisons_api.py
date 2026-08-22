"""API tests: competitor comparisons."""


def _setup(client, headers):
    website = client.post("/api/v1/websites", json={
        "name": "My Site", "url": "https://example.com",
    }, headers=headers)
    assert website.status_code == 201, website.text
    website_id = website.json()["id"]

    competitor_a = client.post(f"/api/v1/websites/{website_id}/competitors", json={
        "name": "Competitor A", "url": "https://example.org",
    }, headers=headers)
    competitor_b = client.post(f"/api/v1/websites/{website_id}/competitors", json={
        "name": "Competitor B", "url": "https://example.net",
    }, headers=headers)
    assert competitor_a.status_code == 201
    assert competitor_b.status_code == 201
    return website_id, competitor_a.json()["id"], competitor_b.json()["id"]


def test_comparison_returns_site_entries(client, auth_headers):
    website_id, comp_a, comp_b = _setup(client, auth_headers)
    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "competitor_ids": [comp_a, comp_b],
    }, headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["sites"]) == 3
    self_entry = next(s for s in data["sites"] if s["is_self"])
    assert self_entry["website_id"] == website_id
    assert self_entry["scores"] == {}  # no completed scan yet
    assert all(s["website_id"] is not None for s in data["sites"])


def test_comparison_with_website_ids(client, auth_headers):
    website_id, _, _ = _setup(client, auth_headers)
    other_a = client.post("/api/v1/websites", json={
        "name": "Other Site A", "url": "https://other-a.example",
    }, headers=auth_headers).json()
    other_b = client.post("/api/v1/websites", json={
        "name": "Other Site B", "url": "https://other-b.example",
    }, headers=auth_headers).json()

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "website_ids": [other_a["id"], other_b["id"]],
    }, headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["sites"]) == 3
    assert any(not s["is_self"] and s["website_id"] == other_a["id"] for s in data["sites"])
    assert any(not s["is_self"] and s["website_id"] == other_b["id"] for s in data["sites"])


def test_comparison_mixed_website_and_competitor_ids(client, auth_headers):
    website_id, comp_a, _ = _setup(client, auth_headers)
    other = client.post("/api/v1/websites", json={
        "name": "Other Site", "url": "https://other.example",
    }, headers=auth_headers).json()

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "competitor_ids": [comp_a],
        "website_ids": [other["id"]],
    }, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["sites"]) == 3


def test_comparison_website_ids_must_be_own(client, auth_headers):
    website_id, _, _ = _setup(client, auth_headers)
    other = client.post("/api/v1/auth/register", json={
        "email": "other@example.com", "password": "strongpass123", "full_name": "Other",
    }).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    other_ws = client.post("/api/v1/websites", json={
        "name": "Other Site", "url": "https://example.net",
    }, headers=other_headers).json()

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "website_ids": [other_ws["id"]],
    }, headers=auth_headers)
    assert response.status_code == 404


def test_comparison_rejects_comparing_with_self(client, auth_headers):
    website_id, _, _ = _setup(client, auth_headers)
    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "website_ids": [website_id],
    }, headers=auth_headers)
    assert response.status_code == 422


def test_comparison_requires_own_competitors(client, auth_headers):
    website_id, _, _ = _setup(client, auth_headers)
    other = client.post("/api/v1/auth/register", json={
        "email": "other@example.com", "password": "strongpass123", "full_name": "Other",
    }).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    other_ws = client.post("/api/v1/websites", json={
        "name": "Other Site", "url": "https://example.net",
    }, headers=other_headers).json()
    other_comp = client.post(f"/api/v1/websites/{other_ws['id']}/competitors", json={
        "name": "Other Competitor", "url": "https://example.org",
    }, headers=other_headers).json()

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "competitor_ids": [other_comp["id"]],
    }, headers=auth_headers)
    assert response.status_code == 404


def test_comparison_uses_scan_of_website_matching_competitor_url(client, auth_headers):
    """Competitors resolve their scores from the user's own website scans."""
    website_id, comp_a, _ = _setup(client, auth_headers)

    # The user has also added the competitor URL as a website and scanned it.
    competitor_ws = client.post("/api/v1/websites", json={
        "name": "Competitor Site", "url": "https://example.org",
    }, headers=auth_headers).json()
    scan = client.post(
        f"/api/v1/scans/websites/{competitor_ws['id']}", json={}, headers=auth_headers
    ).json()
    assert scan["status"] == "COMPLETED", scan["error_message"]

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "competitor_ids": [comp_a],
    }, headers=auth_headers)
    assert response.status_code == 200, response.text
    competitor_entry = next(s for s in response.json()["sites"] if not s["is_self"])
    assert competitor_entry["scores"]["overall"] == scan["overall_score"]
    assert competitor_entry["scan_id"] == scan["id"]


def test_comparison_ai_explanation_present(client, auth_headers):
    website_id, comp_a, _ = _setup(client, auth_headers)
    competitor_ws = client.post("/api/v1/websites", json={
        "name": "Competitor Site", "url": "https://example.org",
    }, headers=auth_headers).json()
    client.post(f"/api/v1/scans/websites/{competitor_ws['id']}", json={}, headers=auth_headers)

    response = client.post("/api/v1/comparisons", json={
        "website_id": website_id,
        "competitor_ids": [comp_a],
    }, headers=auth_headers)
    assert response.status_code == 200, response.text
    # Mock provider returns nothing usable; the deterministic fallback must
    # produce an explanation.
    assert response.json()["ai_explanation"]
