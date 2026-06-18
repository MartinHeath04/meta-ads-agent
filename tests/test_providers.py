"""Tests for the DataProvider abstraction and the seeded FakeDataProvider."""

from data_layer.providers import DataProvider, FakeDataProvider
from data_layer.models import Campaign, AdSet, Ad, Insights


def test_fake_provider_satisfies_protocol():
    assert isinstance(FakeDataProvider(), DataProvider)


def test_get_campaigns_excludes_marketplace():
    """Business rule: marketplace boosted listings are never returned."""
    campaigns = FakeDataProvider().get_campaigns(status_filter=["ACTIVE"])
    assert campaigns, "expected seeded campaigns"
    assert all("Marketplace listing boosted" not in c.name for c in campaigns)
    assert all(isinstance(c, Campaign) for c in campaigns)


def test_status_filter_is_honored():
    provider = FakeDataProvider()
    assert provider.get_campaigns(status_filter=["PAUSED"]) == []
    assert provider.get_campaigns(status_filter=["ACTIVE"])


def test_insights_are_id_keyed_dicts():
    provider = FakeDataProvider()
    ci = provider.get_campaign_insights(date_preset="last_7d")
    assert isinstance(ci, dict)
    assert "camp_messages_spring" in ci
    assert all(isinstance(v, Insights) for v in ci.values())
    # CTR is derived in Insights.__post_init__ from clicks/impressions.
    assert ci["camp_messages_spring"].ctr > 0


def test_adsets_and_ads_link_to_seeded_campaigns():
    provider = FakeDataProvider()
    adsets = provider.get_ad_sets(status_filter=["ACTIVE"])
    ads = provider.get_ads(status_filter=["ACTIVE"])
    assert all(isinstance(a, AdSet) for a in adsets)
    assert all(isinstance(a, Ad) for a in ads)
    campaign_ids = {c.id for c in provider.get_campaigns()}
    assert {a.campaign_id for a in adsets} <= campaign_ids


def test_demo_pipeline_filters_and_aligns(tmp_path):
    """End-to-end fetch via MetaAdsAgent against the fake provider (no network/creds)."""
    from agent.core import MetaAdsAgent
    from agent.brain import AgentBrain
    from agent.memory import AgentMemory

    provider = FakeDataProvider()
    brain = AgentBrain(api_key="test")  # offline; no network at construction
    memory = AgentMemory(db_path=str(tmp_path / "demo.db"))
    agent = MetaAdsAgent(meta_client=provider, brain=brain, memory=memory, dry_run=True)

    data = agent._fetch_all_data("last_7d")

    # Marketplace excluded; both delivering campaigns survive the stale filter.
    names = [c.name for c in data["campaigns"]]
    assert all("Marketplace listing boosted" not in n for n in names)
    assert len(data["campaigns"]) == 2

    # Insights align to the returned campaigns.
    for c in data["campaigns"]:
        assert c.id in data["campaign_insights"]
