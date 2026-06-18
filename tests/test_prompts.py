"""Tests for the agent's system prompt construction."""

from agent.prompts import build_system_prompt
from config.profiles import BusinessProfile, DEFAULT_PROFILE

# The shared, detailing-vertical guidance is built from the default profile.
SYSTEM_PROMPT = build_system_prompt(DEFAULT_PROFILE)


def test_system_prompt_includes_industry_benchmarks():
    """The system prompt should ground the agent with an industry benchmarks block."""
    assert "INDUSTRY BENCHMARKS" in SYSTEM_PROMPT


def test_benchmarks_cover_the_priority_metrics():
    """Benchmarks should reference the efficiency/engagement metrics the agent optimizes for."""
    assert "Cost per message" in SYSTEM_PROMPT
    assert "Click-through rate" in SYSTEM_PROMPT


def test_benchmarks_are_framed_as_soft_guidance():
    """Benchmarks are a yardstick, not hard rules — guard against them being read as thresholds."""
    assert "NOT hard rules" in SYSTEM_PROMPT


def test_system_prompt_explains_campaign_types():
    """The agent must know how boosted posts differ from structured campaigns."""
    assert "CAMPAIGN TYPES" in SYSTEM_PROMPT
    assert "Boosted post" in SYSTEM_PROMPT
    assert "Structured campaign" in SYSTEM_PROMPT


def test_default_profile_renders_its_business():
    """The default profile should still produce the original Sea Street prompt."""
    assert "Sea Street Detailing" in SYSTEM_PROMPT
    assert "Interior boat detailing" in SYSTEM_PROMPT  # a default service


def test_prompt_is_tenant_specific():
    """A different tenant's profile drives the prompt — no other tenant's identity leaks in."""
    profile = BusinessProfile(
        business_name="Acme Boat Care",
        service_type="boat detailing",
        location="Florida",
        service_area=["FL"],
        services=["Hull cleaning", "Ceramic coating"],
        audience_context="Florida boat owners",
    )
    prompt = build_system_prompt(profile)
    assert "Acme Boat Care" in prompt
    assert "Florida" in prompt
    assert "Hull cleaning" in prompt
    assert "Sea Street Detailing" not in prompt


def test_shared_guidance_is_tenant_agnostic():
    """Benchmarks + campaign-type guidance are shared regardless of tenant."""
    profile = BusinessProfile(
        business_name="Acme Boat Care",
        service_type="boat detailing",
        location="Florida",
        service_area=["FL"],
        services=["Hull cleaning"],
    )
    prompt = build_system_prompt(profile)
    assert "INDUSTRY BENCHMARKS" in prompt
    assert "CAMPAIGN TYPES" in prompt


def test_brain_uses_profile_system_prompt():
    """AgentBrain builds its system prompt from the injected profile (offline; dummy key)."""
    from agent.brain import AgentBrain

    profile = BusinessProfile(
        business_name="Acme Boat Care",
        service_type="boat detailing",
        location="Florida",
        service_area=["FL"],
        services=["Hull cleaning"],
    )
    brain = AgentBrain(api_key="test", business_profile=profile)
    assert "Acme Boat Care" in brain.system_prompt
    assert brain.business_profile.business_name == "Acme Boat Care"
