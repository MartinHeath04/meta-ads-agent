"""Tests for the agent's system prompt construction."""

from agent.prompts import SYSTEM_PROMPT


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
