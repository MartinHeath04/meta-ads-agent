"""Tests for the tenant-scoped proposed-actions (human-in-the-loop) queue."""

from agent.memory import AgentMemory
from agent.actions import ProposedAction, ActionStatus, ActionType


def _action(action_type=ActionType.PAUSE_ADSET.value, target="Boosted post audience"):
    return ProposedAction(
        id=None,
        timestamp="2026-06-22T10:00:00",
        action_type=action_type,
        target_type="adset",
        target_id="adset_boost",
        target_name=target,
        rationale="Cost per message 2x the account average over 7 days.",
        confidence="high",
        parameters={"note": "monitor first"},
    )


def test_propose_and_list(tmp_path):
    mem = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id="acme")
    action_id = mem.propose_action(_action())
    assert isinstance(action_id, int)

    actions = mem.list_actions()
    assert len(actions) == 1
    a = actions[0]
    assert a.id == action_id
    assert a.status == ActionStatus.PROPOSED.value
    assert a.parameters == {"note": "monitor first"}


def test_status_filter_and_approve(tmp_path):
    mem = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id="acme")
    aid = mem.propose_action(_action())

    assert len(mem.list_actions(status="proposed")) == 1
    assert mem.list_actions(status="approved") == []

    assert mem.set_action_status(aid, ActionStatus.APPROVED.value) is True
    assert mem.get_action(aid).status == "approved"
    assert mem.list_actions(status="approved")[0].id == aid


def test_reject(tmp_path):
    mem = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id="acme")
    aid = mem.propose_action(_action())
    assert mem.set_action_status(aid, ActionStatus.REJECTED.value) is True
    assert mem.get_action(aid).status == "rejected"


def test_actions_are_tenant_isolated(tmp_path):
    db = str(tmp_path / "shared.db")
    acme = AgentMemory(db_path=db, tenant_id="acme")
    bravo = AgentMemory(db_path=db, tenant_id="bravo")

    aid = acme.propose_action(_action(target="Acme adset"))

    assert len(acme.list_actions()) == 1
    assert bravo.list_actions() == []
    # bravo cannot see or mutate acme's action.
    assert bravo.get_action(aid) is None
    assert bravo.set_action_status(aid, ActionStatus.APPROVED.value) is False
    assert acme.get_action(aid).status == "proposed"


def test_set_status_unknown_id_returns_false(tmp_path):
    mem = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id="acme")
    assert mem.set_action_status(999, ActionStatus.APPROVED.value) is False
