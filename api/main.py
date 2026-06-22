"""FastAPI application for the multi-tenant Meta Ads agent.

Serves the seeded demo tenants over HTTP so the agent is demoable without live
Meta credentials. Interactive docs at /docs.
"""

from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from config.demo_tenants import DEMO_TENANTS, list_demo_tenants
from config.profiles import BusinessProfile
from agent.actions import ActionStatus
from api import service
from api.service import Analyzer, MemoryProvider, get_analyzer, get_memory_provider
from api.schemas import (
    AnalyzeJob,
    HealthResponse,
    ProposedActionOut,
    ReportOut,
    TenantSummary,
)

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


def _require_tenant(tenant_id: str) -> None:
    if tenant_id not in DEMO_TENANTS:
        raise HTTPException(status_code=404, detail=f"Unknown tenant '{tenant_id}'")


@app.get(
    "/tenants/{tenant_id}/actions",
    response_model=list[ProposedActionOut],
    tags=["actions"],
)
def list_actions(
    tenant_id: str,
    status: Optional[str] = None,
    memory_provider: MemoryProvider = Depends(get_memory_provider),
) -> list[ProposedActionOut]:
    _require_tenant(tenant_id)
    memory = memory_provider(tenant_id)
    return [ProposedActionOut.from_action(a) for a in memory.list_actions(status=status)]


def _set_action_status(
    tenant_id: str, action_id: int, status: str, memory_provider: MemoryProvider
) -> ProposedActionOut:
    _require_tenant(tenant_id)
    memory = memory_provider(tenant_id)
    if not memory.set_action_status(action_id, status):
        raise HTTPException(status_code=404, detail=f"Unknown action '{action_id}'")
    return ProposedActionOut.from_action(memory.get_action(action_id))


@app.post(
    "/tenants/{tenant_id}/actions/{action_id}/approve",
    response_model=ProposedActionOut,
    tags=["actions"],
)
def approve_action(
    tenant_id: str,
    action_id: int,
    memory_provider: MemoryProvider = Depends(get_memory_provider),
) -> ProposedActionOut:
    return _set_action_status(tenant_id, action_id, ActionStatus.APPROVED.value, memory_provider)


@app.post(
    "/tenants/{tenant_id}/actions/{action_id}/reject",
    response_model=ProposedActionOut,
    tags=["actions"],
)
def reject_action(
    tenant_id: str,
    action_id: int,
    memory_provider: MemoryProvider = Depends(get_memory_provider),
) -> ProposedActionOut:
    return _set_action_status(tenant_id, action_id, ActionStatus.REJECTED.value, memory_provider)
