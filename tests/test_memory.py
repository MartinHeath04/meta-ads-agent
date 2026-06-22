"""Tests for tenant-scoped agent memory."""

import sqlite3

from agent.memory import AgentMemory, Decision, Learning
from config.profiles import BusinessProfile, DEFAULT_PROFILE


def _decision(action="Pause underperformer", target="Camp A"):
    return Decision(
        id=None,
        timestamp="2026-06-18T10:00:00",
        action_type="recommendation",
        target_type="campaign",
        target_id="c1",
        target_name=target,
        action=action,
        reason="cost per message too high",
        confidence="high",
    )


def _learning(pattern="Before/after creative converts", success=True):
    return Learning(
        id=None,
        timestamp="2026-06-18T10:00:00",
        pattern_type="creative",
        pattern=pattern,
        evidence="22 messages",
        success=success,
        confidence="high",
    )


def test_decisions_are_isolated_per_tenant(tmp_path):
    db = str(tmp_path / "shared.db")
    acme = AgentMemory(db_path=db, tenant_id="acme")
    bravo = AgentMemory(db_path=db, tenant_id="bravo")

    acme.record_decision(_decision(action="Acme action"))

    acme_actions = [d.action for d in acme.get_recent_decisions()]
    bravo_actions = [d.action for d in bravo.get_recent_decisions()]
    assert "Acme action" in acme_actions
    assert bravo_actions == []  # bravo cannot see acme's decisions


def test_learnings_are_isolated_per_tenant(tmp_path):
    db = str(tmp_path / "shared.db")
    acme = AgentMemory(db_path=db, tenant_id="acme")
    bravo = AgentMemory(db_path=db, tenant_id="bravo")

    acme.record_learning(_learning(pattern="Acme pattern", success=True))

    assert any("Acme pattern" == p.pattern for p in acme.get_successful_patterns())
    assert bravo.get_successful_patterns() == []


def test_outcome_update_does_not_cross_tenants(tmp_path):
    db = str(tmp_path / "shared.db")
    acme = AgentMemory(db_path=db, tenant_id="acme")
    bravo = AgentMemory(db_path=db, tenant_id="bravo")

    decision_id = acme.record_decision(_decision())
    # bravo trying to update acme's decision id is a no-op (scoped by tenant).
    bravo.update_outcome(decision_id, outcome="success")

    acme_decision = acme.get_recent_decisions()[0]
    assert acme_decision.outcome is None


def test_business_profile_slug_derivation():
    assert DEFAULT_PROFILE.tenant_id == "sea-street-detailing"
    p = BusinessProfile(
        business_name="Acme Boat Care!",
        service_type="boat detailing",
        location="FL",
        service_area=["FL"],
        services=["Hull cleaning"],
    )
    assert p.tenant_id == "acme-boat-care"
    # Explicit tenant_id is respected.
    p2 = BusinessProfile(
        business_name="Acme Boat Care",
        tenant_id="custom-id",
        service_type="boat detailing",
        location="FL",
        service_area=["FL"],
        services=["Hull cleaning"],
    )
    assert p2.tenant_id == "custom-id"


def test_legacy_db_is_migrated_and_backfilled(tmp_path):
    """A pre-tenant database (no tenant_id column) is migrated; old rows go to the legacy tenant."""
    db = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_name TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            confidence TEXT NOT NULL,
            outcome TEXT,
            outcome_notes TEXT,
            human_feedback TEXT
        )
    """)
    conn.execute("""
        INSERT INTO agent_decisions
        (timestamp, action_type, target_type, target_id, target_name, action, reason, confidence)
        VALUES ('2026-01-01T00:00:00','recommendation','campaign','c0','Old Camp','Old action','r','high')
    """)
    conn.commit()
    conn.close()

    # Opening it adds the column and backfills the legacy row to sea-street-detailing.
    legacy = AgentMemory(db_path=db, tenant_id="sea-street-detailing")
    assert any(d.action == "Old action" for d in legacy.get_recent_decisions())

    other = AgentMemory(db_path=db, tenant_id="someone-else")
    assert other.get_recent_decisions() == []
