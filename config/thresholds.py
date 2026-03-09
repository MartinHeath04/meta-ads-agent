"""
Performance thresholds and business rules for Sea Street Detailing.
These values can be adjusted based on historical performance data.
"""

from dataclasses import dataclass


@dataclass
class ThresholdConfig:
    """Business rules and thresholds for analysis decisions."""

    # ======================
    # Minimum Data Requirements
    # ======================
    # Don't make decisions without enough data
    min_spend_for_decision: float = 20.0  # USD
    min_impressions_for_decision: int = 1000
    min_days_for_trend: int = 3

    # ======================
    # Performance Thresholds
    # ======================
    # Adjust these based on Sea Street Detailing's historical performance
    # Note: "leads" for this business = messages received (not form submissions)
    max_cost_per_lead: float = 50.0  # USD - above this is too expensive per message
    min_ctr_threshold: float = 0.5  # percent - below this is poor engagement
    max_cpm_threshold: float = 30.0  # USD - above this is expensive reach
    max_frequency_threshold: float = 3.0  # ad fatigue warning threshold

    # ======================
    # Budget Adjustment Rules
    # ======================
    budget_increase_max_percent: float = 20.0  # never increase more than 20%
    budget_decrease_max_percent: float = 30.0  # never decrease more than 30%

    # ======================
    # Wasted Spend Detection
    # ======================
    wasted_spend_min_amount: float = 30.0  # USD spent with no results
    wasted_spend_zero_leads_days: int = 3  # days with spend but no leads

    # ======================
    # Confidence Requirements
    # ======================
    min_confidence_for_auto_action: float = 0.85  # 85% confidence for auto actions
    min_confidence_for_recommendation: float = 0.6  # 60% for showing recommendation

    # ======================
    # Geographic Analysis
    # ======================
    min_geo_spend_for_analysis: float = 10.0  # USD
    top_geo_count: int = 5  # show top N locations
    bottom_geo_count: int = 3  # flag bottom N locations

    # ======================
    # Comparison Windows
    # ======================
    short_window_days: int = 3
    medium_window_days: int = 7
    long_window_days: int = 14


# Default threshold configuration
DEFAULT_THRESHOLDS = ThresholdConfig()
