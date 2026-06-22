"""Tests for the FastAPI service (read endpoints + analyze flow)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api import service
from api.service import get_analyzer
from api.schemas import ReportOut, RecommendationOut
from config.demo_tenants import DEMO_TENANTS

client = TestClient(app)


@pytest.fixture
def stub_analyzer():
    """Override the analyzer with a fast, LLM-free stub and clear in-memory stores."""
    def _fake(tenant_id: str, date_range: str) -> ReportOut:
        return ReportOut(
            report_id="rep_test",
            tenant_id=tenant_id,
            date_range=date_range,
            generated_at="2026-06-22T00:00:00+00:00",
            model="stub-model",
            tokens_used=123,
            executive_summary="Stubbed summary",
            recommendations=[RecommendationOut(action="Test cheaper audience", priority="1")],
        )

    service.JOBS.clear()
    service.REPORTS.clear()
    app.dependency_overrides[get_analyzer] = lambda: _fake
    yield
    app.dependency_overrides.clear()
    service.JOBS.clear()
    service.REPORTS.clear()


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


def test_analyze_flow_completes_and_report_is_retrievable(stub_analyzer):
    # Kick off analysis (background task runs before TestClient returns).
    r = client.post("/tenants/harbor-shine-detailing/analyze?date_range=last_7d")
    assert r.status_code == 202
    job = r.json()
    assert job["tenant_id"] == "harbor-shine-detailing"
    job_id = job["job_id"]

    # Job is done with a report id.
    jr = client.get(f"/jobs/{job_id}")
    assert jr.status_code == 200
    assert jr.json()["status"] == "done"
    report_id = jr.json()["report_id"]
    assert report_id

    # Report is retrievable and scoped to the tenant.
    rep = client.get(f"/tenants/harbor-shine-detailing/reports/{report_id}")
    assert rep.status_code == 200
    body = rep.json()
    assert body["executive_summary"] == "Stubbed summary"
    assert body["recommendations"][0]["action"] == "Test cheaper audience"


def test_report_is_tenant_scoped(stub_analyzer):
    r = client.post("/tenants/harbor-shine-detailing/analyze")
    report_id = client.get(f"/jobs/{r.json()['job_id']}").json()["report_id"]
    # Same report id under a different tenant path must not resolve.
    other = client.get(f"/tenants/lakeside-marine-detailing/reports/{report_id}")
    assert other.status_code == 404


def test_analyze_unknown_tenant_is_404(stub_analyzer):
    r = client.post("/tenants/not-a-tenant/analyze")
    assert r.status_code == 404


def test_unknown_job_is_404():
    assert client.get("/jobs/nope").status_code == 404
