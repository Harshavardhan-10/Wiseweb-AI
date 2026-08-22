"""Shared test fixtures.

Environment is configured BEFORE any app import so settings resolve to a
file-based SQLite database and eager Celery.
"""

import os
import tempfile
import warnings
from pathlib import Path

# Suppress third-party deprecation noise before importing app modules.
warnings.filterwarnings("ignore", message=r".*httpx2.*")
warnings.filterwarnings("ignore", message=r".*HTTP_422_UNPROCESSABLE_ENTITY.*")

_TEST_DB = Path(tempfile.gettempdir()) / "wisewebai_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["AI_PROVIDER"] = "mock"
os.environ["AI_ENABLED"] = "true"
os.environ["CRAWLER_CONCURRENCY"] = "2"
os.environ["CRAWLER_DELAY"] = "0"
os.environ["CRAWLER_TIMEOUT"] = "5"
os.environ["SEED_DEMO"] = "false"
os.environ["ALLOW_LOCALHOST_SCANS"] = "false"
os.environ["JWT_SECRET"] = "test-secret-key-0123456789abcdef"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    init_db()
    yield
    engine.dispose()
    if _TEST_DB.exists():
        _TEST_DB.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    # Reset all data between tests.
    for table in reversed(Base.metadata.sorted_tables):
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table.name}"))
            conn.commit()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    """Register a user and return auth headers."""
    response = client.post("/api/v1/auth/register", json={
        "email": "tester@example.com",
        "password": "strongpass123",
        "full_name": "Test User",
    })
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
