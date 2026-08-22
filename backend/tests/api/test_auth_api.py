"""API tests: authentication."""


def test_register_returns_tokens_and_user(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "strongpass123",
        "full_name": "New User",
    })
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "new@example.com"


def test_register_duplicate_email_conflict(client, auth_headers):
    response = client.post("/api/v1/auth/register", json={
        "email": "tester@example.com",
        "password": "strongpass123",
        "full_name": "Another",
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "strongpass123",
        "full_name": "Login User",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "strongpass123",
    })
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password_401(client):
    client.post("/api/v1/auth/register", json={
        "email": "bad@example.com",
        "password": "strongpass123",
        "full_name": "Bad User",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "bad@example.com", "password": "wrongpass",
    })
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "tester@example.com"


def test_refresh_flow(client):
    register = client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "password": "strongpass123",
        "full_name": "Refresh User",
    }).json()
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": register["refresh_token"],
    })
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_validation_error_envelope(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "short",
        "full_name": "",
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_special_use_domain_email_accepted(client):
    """The seeded demo account uses demo@wiseweb-ai.local (.local is a
    special-use domain); login must work for it."""
    response = client.post("/api/v1/auth/register", json={
        "email": "demo@wiseweb-ai.local",
        "password": "demopass123",
        "full_name": "Demo User",
    })
    assert response.status_code == 201, response.text
    login = client.post("/api/v1/auth/login", json={
        "email": "demo@wiseweb-ai.local", "password": "demopass123",
    })
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "demo@wiseweb-ai.local"
