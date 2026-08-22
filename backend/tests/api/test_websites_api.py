"""API tests: websites."""


def test_create_website(client, auth_headers):
    response = client.post("/api/v1/websites", json={
        "name": "Example Inc",
        "url": "https://example.com",
        "website_type": "corporate",
    }, headers=auth_headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["normalized_url"] == "https://example.com/"
    assert data["id"] > 0


def test_create_duplicate_website_422(client, auth_headers):
    payload = {"name": "Example Inc", "url": "https://example.com"}
    assert client.post("/api/v1/websites", json=payload, headers=auth_headers).status_code == 201
    response = client.post("/api/v1/websites", json=payload, headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_websites_isolation(client, auth_headers):
    client.post("/api/v1/websites", json={"name": "Mine", "url": "https://mine.com"}, headers=auth_headers)
    # Second user sees none of the first user's websites.
    second = client.post("/api/v1/auth/register", json={
        "email": "second@example.com", "password": "strongpass123", "full_name": "Second",
    }).json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    response = client.get("/api/v1/websites", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_website_and_404(client, auth_headers):
    created = client.post("/api/v1/websites", json={
        "name": "Mine", "url": "https://mine.com",
    }, headers=auth_headers).json()
    response = client.get(f"/api/v1/websites/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert client.get("/api/v1/websites/99999", headers=auth_headers).status_code == 404


def test_invalid_url_rejected(client, auth_headers):
    response = client.post("/api/v1/websites", json={
        "name": "Bad", "url": "javascript:alert(1)",
    }, headers=auth_headers)
    assert response.status_code == 422


def test_delete_website(client, auth_headers):
    created = client.post("/api/v1/websites", json={
        "name": "ToDelete", "url": "https://delete.com",
    }, headers=auth_headers).json()
    response = client.delete(f"/api/v1/websites/{created['id']}", headers=auth_headers)
    assert response.status_code in (200, 204)
    assert client.get(f"/api/v1/websites/{created['id']}", headers=auth_headers).status_code == 404


def test_delete_competitor(client, auth_headers):
    website = client.post("/api/v1/websites", json={
        "name": "Mine", "url": "https://mine.com",
    }, headers=auth_headers).json()
    competitor = client.post(f"/api/v1/websites/{website['id']}/competitors", json={
        "name": "Competitor", "url": "https://competitor.com",
    }, headers=auth_headers).json()

    response = client.delete(
        f"/api/v1/websites/{website['id']}/competitors/{competitor['id']}", headers=auth_headers
    )
    assert response.status_code in (200, 204)
    remaining = client.get(f"/api/v1/websites/{website['id']}/competitors", headers=auth_headers)
    assert remaining.json() == []


def test_delete_competitor_of_other_website_404(client, auth_headers):
    website = client.post("/api/v1/websites", json={
        "name": "Mine", "url": "https://mine.com",
    }, headers=auth_headers).json()
    other = client.post("/api/v1/websites", json={
        "name": "Other", "url": "https://other.com",
    }, headers=auth_headers).json()
    competitor = client.post(f"/api/v1/websites/{other['id']}/competitors", json={
        "name": "Competitor", "url": "https://competitor.com",
    }, headers=auth_headers).json()

    response = client.delete(
        f"/api/v1/websites/{website['id']}/competitors/{competitor['id']}", headers=auth_headers
    )
    assert response.status_code == 404
