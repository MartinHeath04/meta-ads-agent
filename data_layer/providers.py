"""
Data providers.

The agent fetches ad data through a `DataProvider` so the source can be swapped:
- `MetaAPIClient` (data_layer/meta_client.py) is the real, live provider.
- `FakeDataProvider` (below) serves realistic seeded fixtures so the full
  pipeline runs **without live Meta credentials** — for local dev, tests, demos,
  and public deployments (the real ad account is dormant).

Both satisfy the `DataProvider` Protocol, which captures exactly the methods the
agent core calls (see `agent/core.py::_fetch_all_data`).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol, runtime_checkable

from .models import Campaign, AdSet, Ad, Insights


@runtime_checkable
class DataProvider(Protocol):
    """The data-access surface the agent depends on. Implemented by
    `MetaAPIClient` (live) and `FakeDataProvider` (seeded)."""

    def get_account_info(self) -> dict: ...

    def get_campaigns(
        self, status_filter: list[str] = None, limit: int = 100
    ) -> list[Campaign]: ...

    def get_ad_sets(
        self, campaign_id: str = None, status_filter: list[str] = None, limit: int = 200
    ) -> list[AdSet]: ...

    def get_ads(
        self,
        adset_id: str = None,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 500,
    ) -> list[Ad]: ...

    def get_campaign_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]: ...

    def get_adset_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]: ...

    def get_ad_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]: ...


def _insight(entity_id: str, entity_type: str, **metrics) -> Insights:
    """Build an Insights for the trailing 7 days (CTR/CPM/CPC auto-derived)."""
    today = datetime.now(timezone.utc).date()
    return Insights(
        entity_id=entity_id,
        entity_type=entity_type,
        date_start=today - timedelta(days=7),
        date_stop=today,
        **metrics,
    )


class FakeDataProvider:
    """Serves a realistic, seeded detailing dataset — no network, no credentials.

    Mirrors the real client's contract, including filtering out
    "Marketplace listing boosted" campaigns and honoring `status_filter`.
    """

    def __init__(self, profile=None):
        """
        Args:
            profile: Optional BusinessProfile. When given, the account name reflects
                the business and the seeded metrics are varied by a deterministic
                per-tenant factor so each demo tenant's report differs. When omitted,
                returns the generic baseline dataset.
        """
        self.profile = profile
        if profile is not None:
            # Deterministic factor in ~[0.7, 1.3] so each tenant's numbers differ.
            self._factor = 0.7 + (sum(ord(c) for c in profile.tenant_id) % 7) / 10.0
            self._account_name = profile.business_name
        else:
            self._factor = 1.0
            self._account_name = "Demo Detailing Co (seeded)"

        now = datetime.now(timezone.utc)
        established = now - timedelta(days=11)  # >7 days of data, not "new"

        # --- Campaigns (raw seed, including one marketplace listing to be filtered) ---
        self._campaigns: list[Campaign] = [
            Campaign(
                id="camp_messages_spring",
                name="Spring Boat Detail — Messages",
                status="ACTIVE",
                objective="OUTCOME_ENGAGEMENT",
                daily_budget=25.0,
                created_time=established,
                start_time=established,
            ),
            Campaign(
                id="camp_boost_beforeafter",
                name='Post: "Before/After full boat detail — early season"',
                status="ACTIVE",
                objective="OUTCOME_ENGAGEMENT",
                daily_budget=10.0,
                created_time=now - timedelta(days=9),
                start_time=now - timedelta(days=9),
            ),
            # Excluded by get_campaigns() — present to prove the filter works in demo.
            Campaign(
                id="camp_marketplace",
                name="[full boat DETAIL] Marketplace listing boosted on 6/3",
                status="ACTIVE",
                objective=None,
                created_time=now - timedelta(days=8),
            ),
        ]

        # --- Ad sets ---
        self._adsets: list[AdSet] = [
            AdSet(
                id="adset_messages",
                name="NJ Marina Towns 28-65",
                status="ACTIVE",
                campaign_id="camp_messages_spring",
                daily_budget=25.0,
                optimization_goal="CONVERSATIONS",
                targeting={
                    "geo_locations": {"regions": [{"name": "New Jersey"}]},
                    "age_min": 28,
                    "age_max": 65,
                },
                created_time=established,
            ),
            AdSet(
                id="adset_boost",
                name="Boosted post audience",
                status="ACTIVE",
                campaign_id="camp_boost_beforeafter",
                daily_budget=10.0,
                optimization_goal="POST_ENGAGEMENT",
                created_time=now - timedelta(days=9),
            ),
        ]

        # --- Ads (with creative copy) ---
        self._ads: list[Ad] = [
            Ad(
                id="ad_messages",
                name="Messages — before/after carousel",
                status="ACTIVE",
                adset_id="adset_messages",
                campaign_id="camp_messages_spring",
                primary_text="Get your boat looking showroom-new before the season. "
                "Message us for a fast quote — interior + exterior detailing across NJ marinas.",
                headline="Boat detailing, done right",
                call_to_action_type="MESSAGE_PAGE",
                creative_format="carousel (3 images)",
            ),
            Ad(
                id="ad_boost",
                name="Boosted before/after photo",
                status="ACTIVE",
                adset_id="adset_boost",
                campaign_id="camp_boost_beforeafter",
                primary_text="Before & after on a full interior + compound and wax. 🚤",
                headline="",
                call_to_action_type="LEARN_MORE",
                creative_format="single image",
            ),
        ]

        # --- Insights (id-keyed). Base numbers are scaled per tenant (see _scaled).
        #     Structured campaign converts efficiently; the boost reaches more but
        #     costs much more per message. ---
        messages_base = dict(
            spend=180.0, impressions=12000, reach=8200, frequency=1.46,
            clicks=240, link_clicks=205, messages=22,
        )
        boost_base = dict(
            spend=90.0, impressions=15500, reach=11800, frequency=1.31,
            clicks=310, link_clicks=120, messages=6,
        )
        self._campaign_insights: dict[str, Insights] = {
            "camp_messages_spring": self._scaled("camp_messages_spring", "campaign", messages_base),
            "camp_boost_beforeafter": self._scaled("camp_boost_beforeafter", "campaign", boost_base),
        }
        self._adset_insights: dict[str, Insights] = {
            "adset_messages": self._scaled("adset_messages", "adset", messages_base),
            "adset_boost": self._scaled("adset_boost", "adset", boost_base),
        }
        self._ad_insights: dict[str, Insights] = {
            "ad_messages": self._scaled("ad_messages", "ad", messages_base),
            "ad_boost": self._scaled("ad_boost", "ad", boost_base),
        }

    def _scaled(self, entity_id: str, entity_type: str, base: dict) -> Insights:
        """Build an Insights from base metrics scaled by the per-tenant factor."""
        f = self._factor
        spend = round(base["spend"] * f, 2)
        messages = max(1, round(base["messages"] * f))
        return _insight(
            entity_id, entity_type,
            spend=spend,
            impressions=int(base["impressions"] * f),
            reach=int(base["reach"] * f),
            frequency=base["frequency"],
            clicks=int(base["clicks"] * f),
            link_clicks=int(base["link_clicks"] * f),
            messages=messages,
            cost_per_message=round(spend / messages, 2),
        )

    # --- DataProvider interface ---

    def get_account_info(self) -> dict:
        return {
            "name": self._account_name,
            "account_id": "act_DEMO",
            "account_status": 1,
            "currency": "USD",
            "timezone_name": "America/New_York",
        }

    def get_campaigns(self, status_filter: list[str] = None, limit: int = 100) -> list[Campaign]:
        result = []
        for c in self._campaigns:
            if "Marketplace listing boosted" in (c.name or ""):
                continue  # business rule: never track marketplace boosted listings
            if status_filter and c.status not in status_filter:
                continue
            result.append(c)
        return result[:limit]

    def get_ad_sets(
        self, campaign_id: str = None, status_filter: list[str] = None, limit: int = 200
    ) -> list[AdSet]:
        result = []
        for a in self._adsets:
            if campaign_id and a.campaign_id != campaign_id:
                continue
            if status_filter and a.status not in status_filter:
                continue
            result.append(a)
        return result[:limit]

    def get_ads(
        self,
        adset_id: str = None,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 500,
    ) -> list[Ad]:
        result = []
        for ad in self._ads:
            if adset_id and ad.adset_id != adset_id:
                continue
            if campaign_id and ad.campaign_id != campaign_id:
                continue
            if status_filter and ad.status not in status_filter:
                continue
            result.append(ad)
        return result[:limit]

    def get_campaign_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]:
        return dict(self._campaign_insights)

    def get_adset_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]:
        return dict(self._adset_insights)

    def get_ad_insights(self, date_preset: str = "last_7d") -> dict[str, Insights]:
        return dict(self._ad_insights)
