"""
Meta Marketing API Client

Main client for interacting with the Meta Marketing API.
Handles authentication, data fetching, and rate limiting.
"""

import os
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign as FBCampaign
from facebook_business.adobjects.adset import AdSet as FBAdSet
from facebook_business.adobjects.ad import Ad as FBAd
from facebook_business.adobjects.adcreative import AdCreative as FBAdCreative

from .models import Campaign, AdSet, Ad, Insights

logger = logging.getLogger(__name__)


class MetaAPIClient:
    """Client for Meta Marketing API operations."""

    # Standard fields to fetch for each entity type
    CAMPAIGN_FIELDS = [
        "id",
        "name",
        "status",
        "objective",
        "daily_budget",
        "lifetime_budget",
        "created_time",
        "start_time",
        "stop_time",
    ]

    ADSET_FIELDS = [
        "id",
        "name",
        "status",
        "campaign_id",
        "daily_budget",
        "lifetime_budget",
        "targeting",
        "optimization_goal",
        "billing_event",
        "created_time",
        "start_time",
        "end_time",
    ]

    AD_FIELDS = [
        "id",
        "name",
        "status",
        "adset_id",
        "campaign_id",
        "creative",
        "created_time",
    ]

    INSIGHT_FIELDS = [
        "spend",
        "impressions",
        "reach",
        "frequency",
        "clicks",
        "ctr",
        "cpm",
        "cpc",
        "actions",
        "cost_per_action_type",
    ]

    def __init__(self, access_token: str = None, ad_account_id: str = None):
        """
        Initialize the Meta API client.

        Args:
            access_token: Meta API access token. If not provided, reads from META_ACCESS_TOKEN env var.
            ad_account_id: Ad account ID (format: act_XXXXX). If not provided, reads from META_AD_ACCOUNT_ID env var.
        """
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self.ad_account_id = ad_account_id or os.getenv("META_AD_ACCOUNT_ID")

        if not self.access_token:
            raise ValueError("META_ACCESS_TOKEN is required")
        if not self.ad_account_id:
            raise ValueError("META_AD_ACCOUNT_ID is required")

        # Ensure ad_account_id has the act_ prefix
        if not self.ad_account_id.startswith("act_"):
            self.ad_account_id = f"act_{self.ad_account_id}"

        # Initialize the Facebook API
        FacebookAdsApi.init(access_token=self.access_token)
        self.account = AdAccount(self.ad_account_id)

        logger.info(f"MetaAPIClient initialized for account: {self.ad_account_id}")

    def get_account_info(self) -> dict:
        """Get basic account information."""
        return self.account.api_get(fields=[
            "name",
            "account_id",
            "account_status",
            "currency",
            "timezone_name",
        ])

    def get_campaigns(
        self,
        status_filter: list[str] = None,
        limit: int = 100
    ) -> list[Campaign]:
        """
        Fetch all campaigns from the ad account.

        Args:
            status_filter: List of statuses to filter by (e.g., ["ACTIVE", "PAUSED"])
            limit: Maximum number of campaigns to fetch

        Returns:
            List of Campaign objects
        """
        params = {"limit": limit}

        fb_campaigns = self.account.get_campaigns(
            fields=self.CAMPAIGN_FIELDS,
            params=params
        )

        campaigns = []
        for fb_camp in fb_campaigns:
            camp_status = fb_camp.get("status")
            camp_name = fb_camp.get("name", "")

            # Filter by status in Python if status_filter is provided
            if status_filter and camp_status not in status_filter:
                continue

            # Skip Marketplace boosted listings (these are tracked separately if needed)
            if "Marketplace listing boosted" in camp_name:
                continue

            campaign = Campaign(
                id=fb_camp.get("id"),
                name=fb_camp.get("name"),
                status=camp_status,
                objective=fb_camp.get("objective"),
                daily_budget=self._parse_budget(fb_camp.get("daily_budget")),
                lifetime_budget=self._parse_budget(fb_camp.get("lifetime_budget")),
                created_time=self._parse_datetime(fb_camp.get("created_time")),
                start_time=self._parse_datetime(fb_camp.get("start_time")),
                stop_time=self._parse_datetime(fb_camp.get("stop_time")),
            )
            campaigns.append(campaign)

        logger.info(f"Fetched {len(campaigns)} campaigns")
        return campaigns

    def get_ad_sets(
        self,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 200
    ) -> list[AdSet]:
        """
        Fetch ad sets from the ad account.

        Args:
            campaign_id: If provided, only fetch ad sets from this campaign
            status_filter: List of statuses to filter by
            limit: Maximum number of ad sets to fetch

        Returns:
            List of AdSet objects
        """
        params = {"limit": limit}

        # Don't use API filtering - filter in Python (more reliable per Session 1 findings)
        fb_adsets = self.account.get_ad_sets(
            fields=self.ADSET_FIELDS,
            params=params
        )

        ad_sets = []
        for fb_adset in fb_adsets:
            adset_status = fb_adset.get("status")
            adset_campaign = fb_adset.get("campaign_id")

            # Filter by status in Python
            if status_filter and adset_status not in status_filter:
                continue
            # Filter by campaign in Python
            if campaign_id and adset_campaign != campaign_id:
                continue

            ad_set = AdSet(
                id=fb_adset.get("id"),
                name=fb_adset.get("name"),
                status=adset_status,
                campaign_id=adset_campaign,
                daily_budget=self._parse_budget(fb_adset.get("daily_budget")),
                lifetime_budget=self._parse_budget(fb_adset.get("lifetime_budget")),
                targeting=fb_adset.get("targeting"),
                optimization_goal=fb_adset.get("optimization_goal"),
                billing_event=fb_adset.get("billing_event"),
                created_time=self._parse_datetime(fb_adset.get("created_time")),
                start_time=self._parse_datetime(fb_adset.get("start_time")),
                end_time=self._parse_datetime(fb_adset.get("end_time")),
            )
            ad_sets.append(ad_set)

        logger.info(f"Fetched {len(ad_sets)} ad sets")
        return ad_sets

    def get_ads(
        self,
        adset_id: str = None,
        campaign_id: str = None,
        status_filter: list[str] = None,
        limit: int = 500
    ) -> list[Ad]:
        """
        Fetch ads from the ad account.

        Args:
            adset_id: If provided, only fetch ads from this ad set
            campaign_id: If provided, only fetch ads from this campaign
            status_filter: List of statuses to filter by
            limit: Maximum number of ads to fetch

        Returns:
            List of Ad objects
        """
        params = {"limit": limit}

        # Don't use API filtering - filter in Python (more reliable per Session 1 findings)
        fb_ads = self.account.get_ads(
            fields=self.AD_FIELDS,
            params=params
        )

        ads = []
        for fb_ad in fb_ads:
            ad_status = fb_ad.get("status")
            ad_adset = fb_ad.get("adset_id")
            ad_campaign = fb_ad.get("campaign_id")

            # Filter in Python
            if status_filter and ad_status not in status_filter:
                continue
            if adset_id and ad_adset != adset_id:
                continue
            if campaign_id and ad_campaign != campaign_id:
                continue

            # Extract creative info if available
            creative = fb_ad.get("creative")
            creative_id = None
            if creative and hasattr(creative, "get"):
                creative_id = creative.get("id")
            elif isinstance(creative, dict):
                creative_id = creative.get("id")

            ad = Ad(
                id=fb_ad.get("id"),
                name=fb_ad.get("name"),
                status=ad_status,
                adset_id=ad_adset,
                campaign_id=ad_campaign,
                creative_id=creative_id,
                created_time=self._parse_datetime(fb_ad.get("created_time")),
            )

            # Fetch creative content (ad copy, headline, CTA)
            if creative_id:
                try:
                    cr = FBAdCreative(creative_id).api_get(
                        fields=["body", "title", "name", "object_story_spec"]
                    )
                    ad.primary_text = cr.get("body")
                    ad.headline = cr.get("title")

                    # Extract CTA and creative format from object_story_spec
                    story_spec = cr.get("object_story_spec")
                    if story_spec:
                        link_data = story_spec.get("link_data", {})
                        cta = link_data.get("call_to_action", {})
                        ad.call_to_action_type = cta.get("type")

                        # Determine creative format (carousel, single image, video)
                        children = link_data.get("child_attachments", [])
                        if children:
                            ad.creative_format = f"carousel ({len(children)} images)"
                        elif link_data.get("image_hash"):
                            ad.creative_format = "single image"

                        video_data = story_spec.get("video_data")
                        if video_data:
                            ad.creative_format = "video"

                    if not ad.creative_format:
                        ad.creative_format = "single image" if cr.get("thumbnail_url") else "unknown"
                except Exception as e:
                    logger.warning(f"Could not fetch creative {creative_id}: {e}")

            ads.append(ad)

        logger.info(f"Fetched {len(ads)} ads")
        return ads

    def get_insights(
        self,
        entity_id: str = None,
        entity_type: str = "account",
        date_preset: str = "last_7d",
        time_range: dict = None,
        level: str = None,
        breakdowns: list[str] = None
    ) -> list[Insights]:
        """
        Fetch performance insights.

        Args:
            entity_id: ID of the entity to get insights for (campaign, adset, or ad ID)
            entity_type: Type of entity ('account', 'campaign', 'adset', 'ad')
            date_preset: Predefined date range ('today', 'yesterday', 'last_3d', 'last_7d', 'last_14d', 'last_30d')
            time_range: Custom time range dict with 'since' and 'until' dates (YYYY-MM-DD format)
            level: Aggregation level ('campaign', 'adset', 'ad')
            breakdowns: List of breakdown dimensions (e.g., ['region', 'age'])

        Returns:
            List of Insights objects
        """
        params = {}

        if time_range:
            params["time_range"] = time_range
        else:
            params["date_preset"] = date_preset

        if level:
            params["level"] = level

        if breakdowns:
            params["breakdowns"] = breakdowns

        # Determine which object to query
        if entity_type == "account" or entity_id is None:
            fb_object = self.account
            entity_id = self.ad_account_id
        elif entity_type == "campaign":
            fb_object = FBCampaign(entity_id)
        elif entity_type == "adset":
            fb_object = FBAdSet(entity_id)
        elif entity_type == "ad":
            fb_object = FBAd(entity_id)
        else:
            raise ValueError(f"Unknown entity_type: {entity_type}")

        fb_insights = fb_object.get_insights(
            fields=self.INSIGHT_FIELDS,
            params=params
        )

        insights_list = []
        for fb_insight in fb_insights:
            insights = self._parse_insights(fb_insight, entity_id, entity_type)
            insights_list.append(insights)

        logger.info(f"Fetched {len(insights_list)} insight records for {entity_type} {entity_id}")
        return insights_list

    def get_campaign_insights(
        self,
        date_preset: str = "last_7d",
        time_range: dict = None,
        status_filter: list[str] = None
    ) -> dict[str, Insights]:
        """
        Get insights for all campaigns.

        Args:
            date_preset: Predefined date range
            time_range: Custom time range
            status_filter: Filter campaigns by status

        Returns:
            Dict mapping campaign_id to Insights
        """
        params = {"level": "campaign"}

        if time_range:
            params["time_range"] = time_range
        else:
            params["date_preset"] = date_preset

        if status_filter:
            params["filtering"] = [{"field": "campaign.delivery_status", "operator": "IN", "value": status_filter}]

        fb_insights = self.account.get_insights(
            fields=self.INSIGHT_FIELDS + ["campaign_id", "campaign_name"],
            params=params
        )

        insights_by_campaign = {}
        for fb_insight in fb_insights:
            campaign_id = fb_insight.get("campaign_id")
            insights = self._parse_insights(fb_insight, campaign_id, "campaign")
            insights_by_campaign[campaign_id] = insights

        logger.info(f"Fetched insights for {len(insights_by_campaign)} campaigns")
        return insights_by_campaign

    def get_adset_insights(
        self,
        date_preset: str = "last_7d",
        time_range: dict = None,
        campaign_id: str = None
    ) -> dict[str, Insights]:
        """
        Get insights for all ad sets.

        Args:
            date_preset: Predefined date range
            time_range: Custom time range
            campaign_id: Filter to specific campaign

        Returns:
            Dict mapping adset_id to Insights
        """
        params = {"level": "adset"}

        if time_range:
            params["time_range"] = time_range
        else:
            params["date_preset"] = date_preset

        if campaign_id:
            params["filtering"] = [{"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}]

        fb_insights = self.account.get_insights(
            fields=self.INSIGHT_FIELDS + ["adset_id", "adset_name"],
            params=params
        )

        insights_by_adset = {}
        for fb_insight in fb_insights:
            adset_id = fb_insight.get("adset_id")
            insights = self._parse_insights(fb_insight, adset_id, "adset")
            insights_by_adset[adset_id] = insights

        logger.info(f"Fetched insights for {len(insights_by_adset)} ad sets")
        return insights_by_adset

    def get_ad_insights(
        self,
        date_preset: str = "last_7d",
        time_range: dict = None,
        adset_id: str = None,
        campaign_id: str = None
    ) -> dict[str, Insights]:
        """
        Get insights for all ads.

        Args:
            date_preset: Predefined date range
            time_range: Custom time range
            adset_id: Filter to specific ad set
            campaign_id: Filter to specific campaign

        Returns:
            Dict mapping ad_id to Insights
        """
        params = {"level": "ad"}

        if time_range:
            params["time_range"] = time_range
        else:
            params["date_preset"] = date_preset

        filtering = []
        if adset_id:
            filtering.append({"field": "adset.id", "operator": "EQUAL", "value": adset_id})
        if campaign_id:
            filtering.append({"field": "campaign.id", "operator": "EQUAL", "value": campaign_id})
        if filtering:
            params["filtering"] = filtering

        fb_insights = self.account.get_insights(
            fields=self.INSIGHT_FIELDS + ["ad_id", "ad_name"],
            params=params
        )

        insights_by_ad = {}
        for fb_insight in fb_insights:
            ad_id = fb_insight.get("ad_id")
            insights = self._parse_insights(fb_insight, ad_id, "ad")
            insights_by_ad[ad_id] = insights

        logger.info(f"Fetched insights for {len(insights_by_ad)} ads")
        return insights_by_ad

    def _parse_insights(self, fb_insight: dict, entity_id: str, entity_type: str) -> Insights:
        """Parse Facebook insight data into our Insights model."""
        # Parse actions to extract leads and messages
        leads = 0
        messages = 0
        cost_per_lead = 0.0
        cost_per_message = 0.0
        landing_page_views = 0

        actions = fb_insight.get("actions", [])
        for action in actions:
            action_type = action.get("action_type")
            value = int(action.get("value", 0))

            if action_type == "lead":
                leads = value
            elif action_type in ["onsite_conversion.messaging_conversation_started_7d",
                                  "onsite_conversion.messaging_first_reply"]:
                messages += value
            elif action_type == "landing_page_view":
                landing_page_views = value

        # Parse cost per action
        cost_per_action = fb_insight.get("cost_per_action_type", [])
        for cpa in cost_per_action:
            action_type = cpa.get("action_type")
            value = float(cpa.get("value", 0))

            if action_type == "lead":
                cost_per_lead = value
            elif action_type in ["onsite_conversion.messaging_conversation_started_7d",
                                  "onsite_conversion.messaging_first_reply"]:
                cost_per_message = value

        return Insights(
            entity_id=entity_id,
            entity_type=entity_type,
            date_start=self._parse_date(fb_insight.get("date_start")),
            date_stop=self._parse_date(fb_insight.get("date_stop")),
            spend=float(fb_insight.get("spend", 0)),
            impressions=int(fb_insight.get("impressions", 0)),
            reach=int(fb_insight.get("reach", 0)),
            frequency=float(fb_insight.get("frequency", 0)),
            clicks=int(fb_insight.get("clicks", 0)),
            ctr=float(fb_insight.get("ctr", 0)),
            cpm=float(fb_insight.get("cpm", 0)),
            cpc=float(fb_insight.get("cpc", 0)),
            leads=leads,
            cost_per_lead=cost_per_lead,
            messages=messages,
            cost_per_message=cost_per_message,
            landing_page_views=landing_page_views,
        )

    def _parse_budget(self, value) -> Optional[float]:
        """Parse budget value (comes as cents string)."""
        if value is None:
            return None
        try:
            return float(value) / 100  # Convert cents to dollars
        except (ValueError, TypeError):
            return None

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime string from API."""
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def _parse_date(self, value) -> Optional[date]:
        """Parse date string from API."""
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
