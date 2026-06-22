"""Tests for the seeded demo tenant registry and per-tenant fake data."""

import pytest

from config.demo_tenants import DEMO_TENANTS, get_demo_tenant, list_demo_tenants
from config.profiles import DEFAULT_PROFILE
from data_layer.providers import FakeDataProvider


def test_registry_has_multiple_distinct_detailing_tenants():
    tenants = list_demo_tenants()
    assert len(tenants) >= 2
    ids = [t.tenant_id for t in tenants]
    assert len(ids) == len(set(ids))  # unique
    assert DEFAULT_PROFILE.tenant_id in ids
    assert all("detail" in t.service_type for t in tenants)  # all detailing vertical


def test_get_demo_tenant_lookup_and_error():
    assert get_demo_tenant("harbor-shine-detailing").business_name == "Harbor Shine Detailing"
    with pytest.raises(KeyError):
        get_demo_tenant("not-a-tenant")


def test_provider_reflects_profile_in_account_info():
    profile = get_demo_tenant("harbor-shine-detailing")
    info = FakeDataProvider(profile=profile).get_account_info()
    assert info["name"] == "Harbor Shine Detailing"


def test_provider_varies_metrics_per_tenant():
    a = FakeDataProvider(profile=get_demo_tenant("harbor-shine-detailing"))
    b = FakeDataProvider(profile=get_demo_tenant("lakeside-marine-detailing"))
    spend_a = a.get_campaign_insights()["camp_messages_spring"].spend
    spend_b = b.get_campaign_insights()["camp_messages_spring"].spend
    assert spend_a != spend_b  # different tenants -> different seeded numbers


def test_default_provider_unchanged_without_profile():
    """No profile -> baseline data (factor 1.0) so existing behavior holds."""
    ci = FakeDataProvider().get_campaign_insights()
    assert ci["camp_messages_spring"].spend == 180.0
    assert ci["camp_boost_beforeafter"].messages == 6
