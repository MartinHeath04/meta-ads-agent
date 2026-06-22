"""Pydantic request/response models for the API."""

from typing import Optional

from pydantic import BaseModel

from config.profiles import BusinessProfile
from agent.actions import ProposedAction


class HealthResponse(BaseModel):
    status: str = "ok"


class TenantSummary(BaseModel):
    """Compact view of a tenant for listings."""
    tenant_id: str
    business_name: str
    location: str

    @classmethod
    def from_profile(cls, profile: BusinessProfile) -> "TenantSummary":
        return cls(
            tenant_id=profile.tenant_id,
            business_name=profile.business_name,
            location=profile.location,
        )


class RecommendationOut(BaseModel):
    """A single recommendation from an analysis (parsed from the model's output)."""
    action: str = ""
    target: str = ""
    reason: str = ""
    confidence: str = ""
    risk: str = ""
    priority: str = ""

    @classmethod
    def from_dict(cls, rec: dict) -> "RecommendationOut":
        return cls(
            action=str(rec.get("action", "")),
            target=str(rec.get("target", "")),
            reason=str(rec.get("reason", "")),
            confidence=str(rec.get("confidence", "")),
            risk=str(rec.get("risk", "")),
            priority=str(rec.get("priority", "")),
        )


class ReportOut(BaseModel):
    """A completed analysis report for a tenant."""
    report_id: str
    tenant_id: str
    date_range: str
    generated_at: str
    model: str
    tokens_used: int
    executive_summary: str
    recommendations: list[RecommendationOut] = []


class ProposedActionOut(BaseModel):
    """A proposed action in a tenant's human-in-the-loop approval queue."""
    id: int
    action_type: str
    target_type: str
    target_id: str
    target_name: str
    rationale: str
    confidence: str
    status: str
    created_at: str

    @classmethod
    def from_action(cls, a: ProposedAction) -> "ProposedActionOut":
        return cls(
            id=a.id,
            action_type=a.action_type,
            target_type=a.target_type,
            target_id=a.target_id,
            target_name=a.target_name,
            rationale=a.rationale,
            confidence=a.confidence,
            status=a.status,
            created_at=a.timestamp,
        )


class AnalyzeJob(BaseModel):
    """Status of an analysis run kicked off via POST /analyze."""
    job_id: str
    tenant_id: str
    status: str  # queued | running | done | error
    report_id: Optional[str] = None
    error: Optional[str] = None
