"""
Seeded demo tenants.

A small registry of detailing businesses used to demonstrate the multi-tenant
agent without any live ad accounts. Each is a real-shaped `BusinessProfile`;
combined with `FakeDataProvider`, the agent can analyze any of them in `--demo`
mode with fully isolated memory.

All tenants are in the detailing vertical (shared domain knowledge); only the
business specifics differ.
"""

from config.profiles import BusinessProfile, DEFAULT_PROFILE


DEMO_TENANTS: dict[str, BusinessProfile] = {
    DEFAULT_PROFILE.tenant_id: DEFAULT_PROFILE,
    "harbor-shine-detailing": BusinessProfile(
        business_name="Harbor Shine Detailing",
        tenant_id="harbor-shine-detailing",
        service_type="boat detailing",
        location="Clearwater, Florida",
        service_area=["Tampa Bay", "Clearwater", "St. Petersburg"],
        services=[
            "Saltwater wash-downs",
            "Oxidation removal & compound",
            "Ceramic coating",
            "Hull cleaning",
            "Interior deep clean",
            "Seasonal maintenance plans",
        ],
        audience_context="Gulf Coast boat owners at marinas and yacht clubs",
    ),
    "lakeside-marine-detailing": BusinessProfile(
        business_name="Lakeside Marine Detailing",
        tenant_id="lakeside-marine-detailing",
        service_type="boat and pontoon detailing",
        location="Lake Norman, North Carolina",
        service_area=["Lake Norman", "Mooresville", "Cornelius", "Charlotte lakes"],
        services=[
            "Pontoon detailing",
            "Freshwater hull cleaning",
            "Interior shampoo & vinyl conditioning",
            "Wax & polish",
            "Spring commissioning / winterization prep",
        ],
        audience_context="freshwater lake boat and pontoon owners",
    ),
}


def list_demo_tenants() -> list[BusinessProfile]:
    """All seeded demo tenants."""
    return list(DEMO_TENANTS.values())


def get_demo_tenant(tenant_id: str) -> BusinessProfile:
    """Look up a demo tenant by id, or raise KeyError with the valid options."""
    try:
        return DEMO_TENANTS[tenant_id]
    except KeyError:
        valid = ", ".join(DEMO_TENANTS)
        raise KeyError(f"Unknown demo tenant '{tenant_id}'. Available: {valid}")
