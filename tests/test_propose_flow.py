"""Integration test: agent proposes actions and they land in tenant-scoped memory."""

from agent.core import MetaAdsAgent
from agent.memory import AgentMemory
from agent.actions import ProposedAction, ActionType, ActionStatus
from data_layer.providers import FakeDataProvider
from config.demo_tenants import get_demo_tenant


class StubBrain:
    """A brain that proposes one fixed action, without calling Claude."""

    def __init__(self, business_profile):
        self.business_profile = business_profile

    def propose_actions(self, campaign_data, adset_data, ad_data, date_range="last_7d", **kwargs):
        return [
            ProposedAction(
                id=None,
                timestamp="2026-06-22T10:00:00",
                action_type=ActionType.PAUSE_ADSET.value,
                target_type="adset",
                target_id="adset_boost",
                target_name="Boosted post audience",
                rationale="Cost per message well above the account average.",
                confidence="high",
                status=ActionStatus.PROPOSED.value,
            )
        ]


def test_propose_and_queue_persists_per_tenant(tmp_path):
    profile = get_demo_tenant("harbor-shine-detailing")
    memory = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id=profile.tenant_id)
    agent = MetaAdsAgent(
        meta_client=FakeDataProvider(profile=profile),
        brain=StubBrain(profile),
        memory=memory,
        dry_run=True,
        business_profile=profile,
    )

    actions = agent.propose_and_queue_actions("last_7d")

    assert len(actions) == 1
    assert actions[0].id is not None  # persisted -> got a row id
    # Visible in this tenant's queue...
    queued = memory.list_actions(status="proposed")
    assert len(queued) == 1
    assert queued[0].target_id == "adset_boost"
    # ...and isolated from another tenant.
    other = AgentMemory(db_path=str(tmp_path / "q.db"), tenant_id="lakeside-marine-detailing")
    assert other.list_actions() == []
