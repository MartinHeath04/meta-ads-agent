"""
Per-tenant business profile.

Multi-tenant foundation: the agent's business identity (name, services, service
area) is data, not hardcoded. A BusinessProfile drives the system prompt and
reports so the same detailing-vertical agent can serve many businesses.
"""

import re

from pydantic import BaseModel, Field, model_validator


def slugify(name: str) -> str:
    """Turn a business name into a stable tenant id slug, e.g. 'Acme Boat Care' -> 'acme-boat-care'."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug or "tenant"


class BusinessProfile(BaseModel):
    """Tenant-specific business context that drives prompts and reports.

    Detailing-vertical knowledge (benchmarks, guardrails, success metrics) lives
    in the shared system prompt — only the business-specific fields below vary
    per tenant.
    """

    business_name: str = Field(..., description="e.g. 'Sea Street Detailing'")
    tenant_id: str = Field(
        default="",
        description="Stable tenant identifier; auto-derived from business_name if omitted",
    )
    service_type: str = Field(..., description="e.g. 'boat detailing'")
    location: str = Field(..., description="Primary location, e.g. 'New Jersey'")
    service_area: list[str] = Field(
        ..., description="Areas served, e.g. ['NJ', 'parts of PA and NY']"
    )
    services: list[str] = Field(
        ..., description="Services offered, shown to the agent"
    )
    audience_context: str = Field(
        default="",
        description="Who the ads target, e.g. 'boat owners in waterfront/marina communities'",
    )

    @model_validator(mode="after")
    def _derive_tenant_id(self) -> "BusinessProfile":
        if not self.tenant_id:
            self.tenant_id = slugify(self.business_name)
        return self


# Default profile — the original single-tenant business. Preserves prior behavior
# and serves as the seed/example tenant for the detailing vertical.
DEFAULT_PROFILE = BusinessProfile(
    business_name="Sea Street Detailing",
    tenant_id="sea-street-detailing",
    service_type="boat detailing",
    location="New Jersey",
    service_area=["NJ", "parts of PA and NY (waterfront/marina communities)"],
    services=[
        "Interior boat detailing",
        "Full interior + compound and wax",
        "Full interior + compound / buff / polish / wax",
        "Premium detailing / restoration results",
        "Before-and-after transformation",
        "Mobile/convenience service",
        "Seasonal prep (spring, summer, end-of-season)",
    ],
    audience_context="boat owners in waterfront/marina communities",
)
