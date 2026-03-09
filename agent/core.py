"""
Agent Core - Main Agent Loop

This is the main orchestrator for the Meta Ads Agent. It coordinates
data fetching, LLM analysis, and action execution.
"""

import logging
from datetime import datetime
from typing import Optional

from .brain import AgentBrain, AnalysisResult
from .memory import AgentMemory, Decision
from .actions import ActionExecutor, ActionRequest, ActionType

logger = logging.getLogger(__name__)


class MetaAdsAgent:
    """
    The main Meta Ads AI Agent.

    This agent:
    1. Fetches data from Meta API
    2. Builds context for the LLM
    3. Asks Claude to analyze performance
    4. Generates recommendations
    5. Executes approved actions
    6. Learns from outcomes
    """

    def __init__(
        self,
        meta_client,
        brain: AgentBrain = None,
        memory: AgentMemory = None,
        action_executor: ActionExecutor = None,
        dry_run: bool = True
    ):
        """
        Initialize the agent.

        Args:
            meta_client: Meta API client for data fetching
            brain: LLM brain for analysis (creates default if not provided)
            memory: Agent memory for learning (creates default if not provided)
            action_executor: For executing actions (creates default if not provided)
            dry_run: If True, don't actually execute actions
        """
        self.meta_client = meta_client
        self.brain = brain or AgentBrain()
        self.memory = memory or AgentMemory()
        self.action_executor = action_executor or ActionExecutor(meta_client, dry_run=dry_run)
        self.dry_run = dry_run

        logger.info(f"MetaAdsAgent initialized (dry_run={dry_run})")

    def run_daily_analysis(self, date_range: str = "last_7d") -> AnalysisResult:
        """
        Run the daily analysis workflow.

        1. Fetch all data from Meta API
        2. Build context with data + history
        3. Send to Claude for analysis
        4. Parse recommendations
        5. Save to memory

        Args:
            date_range: Time range to analyze

        Returns:
            AnalysisResult with insights and recommendations
        """
        logger.info(f"Starting daily analysis for {date_range}")

        # Step 1: Fetch data
        logger.info("Fetching data from Meta API...")
        data = self._fetch_all_data(date_range)

        # Step 2: Build context
        logger.info("Building analysis context...")
        campaign_data = self._format_campaign_data(data["campaigns"], data["campaign_insights"])
        adset_data = self._format_adset_data(data["adsets"], data["adset_insights"])
        ad_data = self._format_ad_data(data["ads"], data["ad_insights"])
        historical_context = self.memory.get_context_for_analysis()

        # Step 3: Run LLM analysis
        logger.info("Sending to Claude for analysis...")
        result = self.brain.analyze(
            campaign_data=campaign_data,
            adset_data=adset_data,
            ad_data=ad_data,
            historical_context=historical_context,
            date_range=date_range
        )

        # Step 4: Save analysis to memory
        self.memory.save_analysis(
            date_range=date_range,
            raw_response=result.raw_response,
            executive_summary=result.executive_summary,
            tokens_used=result.tokens_used,
            model=result.model
        )

        # Step 5: Record recommendations as pending decisions
        for rec in result.recommendations:
            decision = Decision(
                id=None,
                timestamp=datetime.now().isoformat(),
                action_type="recommendation",
                target_type=rec.get("target", "unknown").split()[0] if rec.get("target") else "unknown",
                target_id="",  # Would need to parse from target
                target_name=rec.get("target", "unknown"),
                action=rec.get("action", ""),
                reason=rec.get("reason", ""),
                confidence=rec.get("confidence", "medium"),
                outcome="pending"
            )
            self.memory.record_decision(decision)

        logger.info(f"Analysis complete. {len(result.recommendations)} recommendations generated.")
        return result

    def run_quick_check(self) -> str:
        """
        Run a quick health check on the account.

        Returns a brief summary of top issues and wins.
        """
        logger.info("Running quick check...")

        data = self._fetch_all_data("last_3d")

        # Format a summary for quick analysis
        summary = self._build_quick_summary(data)

        return self.brain.quick_analyze(summary)

    def process_recommendation(
        self,
        recommendation: dict,
        approved: bool,
        feedback: str = ""
    ):
        """
        Process a recommendation - approve or reject it.

        Args:
            recommendation: The recommendation dict from analysis
            approved: Whether the recommendation is approved
            feedback: Optional human feedback
        """
        if approved:
            # Create action request
            action_type = self._map_recommendation_to_action(recommendation)
            if action_type:
                request = ActionRequest(
                    action_type=action_type,
                    target_type=recommendation.get("target", "").split()[0],
                    target_id="",  # Would need to extract
                    target_name=recommendation.get("target", "unknown"),
                    reason=recommendation.get("reason", ""),
                    confidence=recommendation.get("confidence", "medium"),
                    risk=recommendation.get("risk", "medium"),
                )

                request = self.action_executor.approve(request)
                result = self.action_executor.execute(request)

                logger.info(f"Action result: {result.success}")
        else:
            logger.info(f"Recommendation rejected: {recommendation.get('action', 'unknown')}")

        # Record feedback
        if feedback:
            # Would need to link to specific decision
            logger.info(f"Human feedback recorded: {feedback}")

    def _fetch_all_data(self, date_range: str) -> dict:
        """Fetch all data from Meta API, excluding marketplace boosted ads."""
        # Get account info
        account_info = self.meta_client.get_account_info()

        # Get campaigns (already excludes marketplace boosted listings)
        campaigns = self.meta_client.get_campaigns(status_filter=["ACTIVE"])
        valid_campaign_ids = {c.id for c in campaigns}

        logger.info(f"Valid campaign IDs (non-marketplace): {valid_campaign_ids}")

        # Get ad sets - only from valid campaigns
        all_adsets = self.meta_client.get_ad_sets(status_filter=["ACTIVE"])
        adsets = [a for a in all_adsets if a.campaign_id in valid_campaign_ids]
        valid_adset_ids = {a.id for a in adsets}

        logger.info(f"Filtered ad sets: {len(adsets)} of {len(all_adsets)} (excluded marketplace)")

        # Get ads - only from valid ad sets
        all_ads = self.meta_client.get_ads(status_filter=["ACTIVE"])
        ads = [a for a in all_ads if a.adset_id in valid_adset_ids]

        logger.info(f"Filtered ads: {len(ads)} of {len(all_ads)} (excluded marketplace)")

        # Get insights - filter to only valid campaigns/adsets/ads
        all_campaign_insights = self.meta_client.get_campaign_insights(date_preset=date_range)
        campaign_insights = {k: v for k, v in all_campaign_insights.items() if k in valid_campaign_ids}

        all_adset_insights = self.meta_client.get_adset_insights(date_preset=date_range)
        adset_insights = {k: v for k, v in all_adset_insights.items() if k in valid_adset_ids}

        valid_ad_ids = {a.id for a in ads}
        all_ad_insights = self.meta_client.get_ad_insights(date_preset=date_range)
        ad_insights = {k: v for k, v in all_ad_insights.items() if k in valid_ad_ids}

        return {
            "account_info": account_info,
            "campaigns": campaigns,
            "adsets": adsets,
            "ads": ads,
            "campaign_insights": campaign_insights,
            "adset_insights": adset_insights,
            "ad_insights": ad_insights,
        }

    def _format_campaign_data(self, campaigns: list, insights: dict) -> str:
        """Format campaign data for the LLM."""
        if not campaigns:
            return "No active campaigns found."

        lines = []
        for campaign in campaigns:
            insight = insights.get(campaign.id)
            if insight:
                lines.append(f"""
**{campaign.name}** (ID: {campaign.id})
- Status: {campaign.status}
- Objective: {campaign.objective or 'N/A'}
- Spend: ${insight.spend:.2f}
- Impressions: {insight.impressions:,}
- Clicks: {insight.clicks:,}
- CTR: {insight.ctr:.2f}%
- Messages: {insight.messages}
- Cost/Message: {'${:.2f}'.format(insight.cost_per_message) if insight.cost_per_message else 'N/A'}
""")
            else:
                lines.append(f"""
**{campaign.name}** (ID: {campaign.id})
- Status: {campaign.status}
- No performance data available
""")

        return "\n".join(lines) if lines else "No campaign data available."

    def _format_adset_data(self, adsets: list, insights: dict) -> str:
        """Format ad set data for the LLM."""
        if not adsets:
            return "No active ad sets found."

        lines = []
        for adset in adsets:
            insight = insights.get(adset.id)
            if insight:
                lines.append(f"""
**{adset.name}** (ID: {adset.id})
- Campaign: {adset.campaign_id}
- Status: {adset.status}
- Spend: ${insight.spend:.2f}
- Impressions: {insight.impressions:,}
- Clicks: {insight.clicks:,}
- CTR: {insight.ctr:.2f}%
- Messages: {insight.messages}
""")

        return "\n".join(lines) if lines else "No ad set data available."

    def _format_ad_data(self, ads: list, insights: dict) -> str:
        """Format ad data including copy for the LLM."""
        if not ads:
            return "No active ads found."

        lines = []
        for ad in ads:
            insight = insights.get(ad.id)
            if insight:
                lines.append(f"""
**{ad.name}** (ID: {ad.id})
- Ad Set: {ad.adset_id}
- Status: {ad.status}
- Primary Text: {ad.primary_text or 'N/A'}
- Headline: {ad.headline or 'N/A'}
- CTA: {ad.call_to_action_type or 'N/A'}
- Spend: ${insight.spend:.2f}
- Impressions: {insight.impressions:,}
- Clicks: {insight.clicks:,}
- CTR: {insight.ctr:.2f}%
- Messages: {insight.messages}
- Cost/Message: {'${:.2f}'.format(insight.cost_per_message) if insight.cost_per_message else 'N/A'}
""")

        return "\n".join(lines) if lines else "No ad data available."

    def _build_quick_summary(self, data: dict) -> str:
        """Build a quick summary for fast analysis."""
        campaigns = data["campaigns"]
        insights = data["campaign_insights"]

        total_spend = sum(i.spend for i in insights.values())
        total_messages = sum(i.messages for i in insights.values())

        return f"""
Account Summary (Last 3 Days):
- Total Spend: ${total_spend:.2f}
- Total Messages: {total_messages}
- Active Campaigns: {len(campaigns)}
- Cost per Message: ${total_spend/total_messages:.2f if total_messages else 'N/A'}

Top campaigns by spend:
{self._format_campaign_data(campaigns[:5], insights)}
"""

    def _map_recommendation_to_action(self, rec: dict) -> Optional[ActionType]:
        """Map a recommendation to an action type."""
        action_text = rec.get("action", "").lower()

        if "pause" in action_text and "ad" in action_text:
            return ActionType.PAUSE_AD
        elif "pause" in action_text and "adset" in action_text:
            return ActionType.PAUSE_ADSET
        elif "reduce" in action_text and "budget" in action_text:
            return ActionType.REDUCE_BUDGET
        elif "increase" in action_text and "budget" in action_text:
            return ActionType.INCREASE_BUDGET

        return None

    def generate_report(self, result: AnalysisResult) -> str:
        """
        Generate a formatted report from analysis results.

        Args:
            result: The analysis result from run_daily_analysis

        Returns:
            Formatted markdown report
        """
        report = f"""# Sea Street Detailing - Meta Ads Analysis Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Model:** {result.model}
**Tokens Used:** {result.tokens_used:,}

---

## Executive Summary

{result.executive_summary}

---

## Performance Analysis

{result.performance_analysis}

---

## Copy Insights

{result.copy_insights}

---

## Creative Insights

{result.creative_insights}

---

## Geographic Insights

{result.geographic_insights}

---

## Recommended Actions

"""
        for i, rec in enumerate(result.recommendations, 1):
            report += f"""
### {i}. {rec.get('action', 'Unknown Action')}
- **Target:** {rec.get('target', 'N/A')}
- **Reason:** {rec.get('reason', 'N/A')}
- **Evidence:** {rec.get('evidence', 'N/A')}
- **Confidence:** {rec.get('confidence', 'N/A')}
- **Risk:** {rec.get('risk', 'N/A')}
- **Priority:** {rec.get('priority', 'N/A')}
"""

        return report
