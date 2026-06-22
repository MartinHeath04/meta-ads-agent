"""FastAPI application for the multi-tenant Meta Ads agent.

Serves the seeded demo tenants over HTTP so the agent is demoable without live
Meta credentials. Interactive docs at /docs.
"""

from fastapi import FastAPI, HTTPException

from config.demo_tenants import DEMO_TENANTS, list_demo_tenants
from config.profiles import BusinessProfile
from api.schemas import HealthResponse, TenantSummary

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
