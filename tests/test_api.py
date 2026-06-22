"""Tests for the FastAPI service (read endpoints)."""

from fastapi.testclient import TestClient

from api.main import app
from config.demo_tenants import DEMO_TENANTS

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_tenants_returns_all_demo_tenants():
    r = client.get("/tenants")
    assert r.status_code == 200
    ids = {t["tenant_id"] for t in r.json()}
    assert ids == set(DEMO_TENANTS)
    assert len(ids) >= 3


def test_get_tenant_known():
    r = client.get("/tenants/harbor-shine-detailing")
    assert r.status_code == 200
    body = r.json()
    assert body["business_name"] == "Harbor Shine Detailing"
    assert body["tenant_id"] == "harbor-shine-detailing"
    assert "services" in body


def test_get_tenant_unknown_is_404():
    r = client.get("/tenants/not-a-tenant")
    assert r.status_code == 404


def test_openapi_schema_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/tenants" in r.json()["paths"]
