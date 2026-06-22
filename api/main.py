"""FastAPI application for the multi-tenant Meta Ads agent.

Serves the seeded demo tenants over HTTP so the agent is demoable without live
Meta credentials. Interactive docs at /docs.
"""

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from config.demo_tenants import DEMO_TENANTS, list_demo_tenants
from config.profiles import BusinessProfile
from api import service
from api.service import Analyzer, get_analyzer
from api.schemas import AnalyzeJob, HealthResponse, ReportOut, TenantSummary

app = FastAPI(
    title="Meta Ads AI Agent",
    description="Multi-tenant AI agent for detailing ad ops (demo tenants).",
    version="0.1.0",
)


@app.get("/healthz", response_model=HealthResponse, tags=["meta"])
def healthz() -> HealthResponse:
    return HealthResponse()


@app.get("/tenants", response_model=list[TenantSummary], tags=["tenants"])
def list_tenants() -> list[TenantSummary]:
    return [TenantSummary.from_profile(p) for p in list_demo_tenants()]


@app.get("/tenants/{tenant_id}", response_model=BusinessProfile, tags=["tenants"])
def get_tenant(tenant_id: str) -> BusinessProfile:
    profile = DEMO_TENANTS.get(tenant_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Unknown tenant '{tenant_id}'")
    return profile


@app.post(
    "/tenants/{tenant_id}/analyze",
    response_model=AnalyzeJob,
    status_code=202,
    tags=["analysis"],
)
def analyze(
    tenant_id: str,
    background: BackgroundTasks,
    date_range: str = "last_7d",
    analyzer: Analyzer = Depends(get_analyzer),
) -> AnalyzeJob:
    if tenant_id not in DEMO_TENANTS:
        raise HTTPException(status_code=404, detail=f"Unknown tenant '{tenant_id}'")
    job = service.create_job(tenant_id)
    background.add_task(service.run_job, job.job_id, tenant_id, date_range, analyzer)
    return job


@app.get("/jobs/{job_id}", response_model=AnalyzeJob, tags=["analysis"])
def get_job(job_id: str) -> AnalyzeJob:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job '{job_id}'")
    return job


@app.get(
    "/tenants/{tenant_id}/reports/{report_id}",
    response_model=ReportOut,
    tags=["analysis"],
)
def get_report(tenant_id: str, report_id: str) -> ReportOut:
    report = service.get_report(report_id)
    if report is None or report.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"Unknown report '{report_id}'")
    return report
