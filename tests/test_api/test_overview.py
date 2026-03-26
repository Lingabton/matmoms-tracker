"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from matmoms.api.app import create_app
from matmoms.api.deps import get_db
from matmoms.db.models import Base
from tests.conftest import _seed_db


@pytest.fixture
def client():
    """FastAPI test client with seeded in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    session = Session(engine)
    _seed_db(session)

    app = create_app()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    session.close()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_overview(client):
    resp = client.get("/api/overview?comparison_date=2026-04-02")
    assert resp.status_code == 200
    data = resp.json()
    assert data["national"]["n_products"] > 0
    assert "passthrough_pct" in data["national"]
    assert "chains" in data


def test_categories(client):
    resp = client.get("/api/categories?comparison_date=2026-04-02")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data


def test_export_csv(client):
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
