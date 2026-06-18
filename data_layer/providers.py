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

    def __init__(self):
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

        # --- Insights (id-keyed). Structured campaign converts efficiently;
        #     the boost reaches more but costs much more per message. ---
        self._campaign_insights: dict[str, Insights] = {
            "camp_messages_spring": _insight(
                "camp_messages_spring", "campaign",
                spend=180.0, impressions=12000, reach=8200, frequency=1.46,
                clicks=240, link_clicks=205, messages=22, cost_per_message=8.18,
            ),
            "camp_boost_beforeafter": _insight(
                "camp_boost_beforeafter", "campaign",
                spend=90.0, impressions=15500, reach=11800, frequency=1.31,
                clicks=310, link_clicks=120, messages=6, cost_per_message=15.0,
            ),
        }
        self._adset_insights: dict[str, Insights] = {
            "adset_messages": _insight(
                "adset_messages", "adset",
                spend=180.0, impressions=12000, reach=8200, frequency=1.46,
                clicks=240, link_clicks=205, messages=22, cost_per_message=8.18,
            ),
            "adset_boost": _insight(
                "adset_boost", "adset",
                spend=90.0, impressions=15500, reach=11800, frequency=1.31,
                clicks=310, link_clicks=120, messages=6, cost_per_message=15.0,
            ),
        }
        self._ad_insights: dict[str, Insights] = {
            "ad_messages": _insight(
                "ad_messages", "ad",
                spend=180.0, impressions=12000, reach=8200, frequency=1.46,
                clicks=240, link_clicks=205, messages=22, cost_per_message=8.18,
            ),
            "ad_boost": _insight(
                "ad_boost", "ad",
                spend=90.0, impressions=15500, reach=11800, frequency=1.31,
                clicks=310, link_clicks=120, messages=6, cost_per_message=15.0,
            ),
        }

    # --- DataProvider interface ---

    def get_account_info(self) -> dict:
        return {
            "name": "Demo Detailing Co (seeded)",
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
