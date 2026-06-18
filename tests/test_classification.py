"""Tests for boosted-post vs structured-campaign classification."""

from data_layer.models import (
    Campaign,
    CampaignType,
    classify_campaign,
    campaign_type_label,
)


def _campaign(name="My Campaign", objective=None):
    return Campaign(id="1", name=name, status="ACTIVE", objective=objective)


def test_generic_boost_name_is_boosted_post():
    assert classify_campaign(_campaign(name="Promoting website: seastreetdetailing.com")) == CampaignType.BOOSTED_POST
    assert classify_campaign(_campaign(name="Promoting your post")) == CampaignType.BOOSTED_POST


def test_boosted_keyword_in_name_is_boosted_post():
    assert classify_campaign(_campaign(name="Spring Boosted Post")) == CampaignType.BOOSTED_POST


def test_name_match_is_case_insensitive():
    assert classify_campaign(_campaign(name="PROMOTING WEBSITE: foo")) == CampaignType.BOOSTED_POST


def test_boost_only_objective_is_boosted_post():
    assert classify_campaign(_campaign(name="Generic Name", objective="POST_ENGAGEMENT")) == CampaignType.BOOSTED_POST
    assert classify_campaign(_campaign(name="Generic Name", objective="PAGE_LIKES")) == CampaignType.BOOSTED_POST


def test_messages_campaign_is_not_misclassified():
    # OUTCOME_ENGAGEMENT is used by real Messages campaigns — must NOT be flagged as a boost.
    c = _campaign(name="Summer Messages - Marina Towns", objective="OUTCOME_ENGAGEMENT")
    assert classify_campaign(c) == CampaignType.CAMPAIGN


def test_structured_campaign_is_campaign():
    c = _campaign(name="Lead Gen - North Jersey", objective="OUTCOME_LEADS")
    assert classify_campaign(c) == CampaignType.CAMPAIGN


def test_label_is_human_readable():
    assert campaign_type_label(_campaign(name="Promoting website: foo")) == "Boosted post"
    assert campaign_type_label(_campaign(name="Lead Gen - NJ")) == "Structured campaign"
