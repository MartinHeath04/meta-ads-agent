"""Tests for context formatting, including campaign-type labeling."""

from datetime import date

from data_layer.context_builder import ContextBuilder
from data_layer.models import Campaign, Insights


def _insight(campaign_id):
    return Insights(
        entity_id=campaign_id,
        entity_type="campaign",
        date_start=date(2026, 6, 1),
        date_stop=date(2026, 6, 7),
        spend=50.0,
        impressions=1000,
        clicks=20,
        messages=5,
    )


def test_boosted_post_is_labeled_in_context():
    builder = ContextBuilder()
    campaign = Campaign(id="1", name="Promoting website: seastreetdetailing.com", status="ACTIVE")
    out = builder.build_campaign_context([campaign], {"1": _insight("1")})
    assert "**Type:** Boosted post" in out


def test_structured_campaign_is_labeled_in_context():
    builder = ContextBuilder()
    campaign = Campaign(id="2", name="Lead Gen - North Jersey", status="ACTIVE", objective="OUTCOME_LEADS")
    out = builder.build_campaign_context([campaign], {"2": _insight("2")})
    assert "**Type:** Structured campaign" in out


def test_type_label_present_even_without_insights():
    builder = ContextBuilder()
    campaign = Campaign(id="3", name="Promoting your post", status="ACTIVE")
    out = builder.build_campaign_context([campaign], {})  # no insights for this campaign
    assert "**Type:** Boosted post" in out
