"""
Context Builder - Structures data for LLM analysis

This module takes raw data from Meta API and formats it into
prompts that the agent brain can analyze effectively.
"""

import logging
from typing import Optional
from datetime import datetime

from .models import Campaign, AdSet, Ad, Insights

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds context strings from Meta Ads data for the LLM.

    Responsible for formatting campaign, ad set, and ad data
    in a way that the LLM can understand and analyze effectively.
    """

    def __init__(self):
        pass

    def build_campaign_context(
        self,
        campaigns: list[Campaign],
        insights: dict[str, Insights]
    ) -> str:
        """
        Build formatted context string for campaigns.

        Args:
            campaigns: List of Campaign objects
            insights: Dict mapping campaign_id to Insights

        Returns:
            Formatted string for LLM
        """
        if not campaigns:
            return "No active campaigns found."

        lines = []

        # Sort by spend descending
        campaigns_with_spend = []
        for campaign in campaigns:
            insight = insights.get(campaign.id)
            spend = insight.spend if insight else 0
            campaigns_with_spend.append((campaign, insight, spend))

        campaigns_with_spend.sort(key=lambda x: x[2], reverse=True)

        for campaign, insight, _ in campaigns_with_spend:
            if insight:
                # Calculate cost per message
                cpm_str = f"${insight.cost_per_message:.2f}" if insight.messages > 0 else "N/A (no messages)"

                lines.append(f"""
### {campaign.name}
- **ID:** {campaign.id}
- **Status:** {campaign.status}
- **Objective:** {campaign.objective or 'Not specified'}
- **Spend:** ${insight.spend:.2f}
- **Impressions:** {insight.impressions:,}
- **Reach:** {insight.reach:,}
- **Clicks:** {insight.clicks:,}
- **CTR:** {insight.ctr:.2f}%
- **CPM:** ${insight.cpm:.2f}
- **Messages:** {insight.messages}
- **Cost per Message:** {cpm_str}
- **Frequency:** {insight.frequency:.2f}
""")
            else:
                lines.append(f"""
### {campaign.name}
- **ID:** {campaign.id}
- **Status:** {campaign.status}
- **No performance data available for this period**
""")

        return "\n".join(lines)

    def build_adset_context(
        self,
        adsets: list[AdSet],
        insights: dict[str, Insights],
        include_targeting: bool = False
    ) -> str:
        """
        Build formatted context string for ad sets.

        Args:
            adsets: List of AdSet objects
            insights: Dict mapping adset_id to Insights
            include_targeting: Whether to include targeting details

        Returns:
            Formatted string for LLM
        """
        if not adsets:
            return "No active ad sets found."

        lines = []

        # Sort by spend descending
        adsets_with_spend = []
        for adset in adsets:
            insight = insights.get(adset.id)
            spend = insight.spend if insight else 0
            adsets_with_spend.append((adset, insight, spend))

        adsets_with_spend.sort(key=lambda x: x[2], reverse=True)

        for adset, insight, _ in adsets_with_spend:
            if insight:
                cpm_str = f"${insight.cost_per_message:.2f}" if insight.messages > 0 else "N/A"

                targeting_str = ""
                if include_targeting and adset.targeting:
                    targeting_str = self._format_targeting(adset.targeting)

                lines.append(f"""
### {adset.name}
- **ID:** {adset.id}
- **Campaign ID:** {adset.campaign_id}
- **Status:** {adset.status}
- **Optimization Goal:** {adset.optimization_goal or 'Not specified'}
- **Spend:** ${insight.spend:.2f}
- **Impressions:** {insight.impressions:,}
- **Clicks:** {insight.clicks:,}
- **CTR:** {insight.ctr:.2f}%
- **Messages:** {insight.messages}
- **Cost per Message:** {cpm_str}
{targeting_str}""")

        return "\n".join(lines)

    def build_ad_context(
        self,
        ads: list[Ad],
        insights: dict[str, Insights]
    ) -> str:
        """
        Build formatted context string for ads including copy.

        Args:
            ads: List of Ad objects with copy populated
            insights: Dict mapping ad_id to Insights

        Returns:
            Formatted string for LLM
        """
        if not ads:
            return "No active ads found."

        lines = []

        # Sort by spend descending
        ads_with_spend = []
        for ad in ads:
            insight = insights.get(ad.id)
            spend = insight.spend if insight else 0
            ads_with_spend.append((ad, insight, spend))

        ads_with_spend.sort(key=lambda x: x[2], reverse=True)

        for ad, insight, _ in ads_with_spend:
            primary_text = ad.primary_text or "No primary text"
            headline = ad.headline or "No headline"
            cta = ad.call_to_action_type or "No CTA"

            # Truncate long text for readability
            if len(primary_text) > 300:
                primary_text = primary_text[:300] + "..."

            if insight:
                cpm_str = f"${insight.cost_per_message:.2f}" if insight.messages > 0 else "N/A"

                lines.append(f"""
### {ad.name}
- **ID:** {ad.id}
- **Ad Set ID:** {ad.adset_id}
- **Status:** {ad.status}

**Ad Copy:**
- Primary Text: "{primary_text}"
- Headline: "{headline}"
- CTA: {cta}

**Performance:**
- Spend: ${insight.spend:.2f}
- Impressions: {insight.impressions:,}
- Clicks: {insight.clicks:,}
- CTR: {insight.ctr:.2f}%
- Messages: {insight.messages}
- Cost per Message: {cpm_str}
""")

        return "\n".join(lines)

    def build_summary_context(
        self,
        campaigns: list[Campaign],
        campaign_insights: dict[str, Insights],
        date_range: str = "last 7 days"
    ) -> str:
        """
        Build a high-level summary context.

        Args:
            campaigns: List of campaigns
            campaign_insights: Insights by campaign
            date_range: Time period description

        Returns:
            Summary string
        """
        total_spend = sum(i.spend for i in campaign_insights.values())
        total_impressions = sum(i.impressions for i in campaign_insights.values())
        total_clicks = sum(i.clicks for i in campaign_insights.values())
        total_messages = sum(i.messages for i in campaign_insights.values())

        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_cpm = (total_spend / total_messages) if total_messages > 0 else 0

        return f"""
## Account Summary ({date_range})

- **Total Spend:** ${total_spend:.2f}
- **Total Impressions:** {total_impressions:,}
- **Total Clicks:** {total_clicks:,}
- **Total Messages (Leads):** {total_messages}
- **Average CTR:** {avg_ctr:.2f}%
- **Average Cost per Message:** ${avg_cpm:.2f if total_messages > 0 else 'N/A'}
- **Active Campaigns:** {len(campaigns)}
"""

    def build_full_context(
        self,
        campaigns: list[Campaign],
        adsets: list[AdSet],
        ads: list[Ad],
        campaign_insights: dict[str, Insights],
        adset_insights: dict[str, Insights],
        ad_insights: dict[str, Insights],
        historical_context: str = "",
        date_range: str = "last 7 days"
    ) -> dict:
        """
        Build complete context for analysis.

        Returns a dict with all context sections ready for the prompt.
        """
        return {
            "summary": self.build_summary_context(campaigns, campaign_insights, date_range),
            "campaigns": self.build_campaign_context(campaigns, campaign_insights),
            "adsets": self.build_adset_context(adsets, adset_insights),
            "ads": self.build_ad_context(ads, ad_insights),
            "historical": historical_context or "No historical data available yet."
        }

    def _format_targeting(self, targeting: dict) -> str:
        """Format targeting info for display."""
        if not targeting:
            return ""

        parts = []

        # Geo targeting
        geo = targeting.get("geo_locations", {})
        if geo:
            cities = geo.get("cities", [])
            regions = geo.get("regions", [])
            if cities:
                parts.append(f"Cities: {', '.join(c.get('name', 'Unknown') for c in cities[:5])}")
            if regions:
                parts.append(f"Regions: {', '.join(r.get('name', 'Unknown') for r in regions[:5])}")

        # Age targeting
        age_min = targeting.get("age_min")
        age_max = targeting.get("age_max")
        if age_min or age_max:
            parts.append(f"Age: {age_min or '18'}-{age_max or '65+'}")

        # Gender
        genders = targeting.get("genders", [])
        if genders:
            gender_map = {1: "Male", 2: "Female"}
            parts.append(f"Gender: {', '.join(gender_map.get(g, 'All') for g in genders)}")

        if parts:
            return "- **Targeting:** " + " | ".join(parts) + "\n"

        return ""
