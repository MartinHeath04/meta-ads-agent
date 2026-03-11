"""
Data models for Meta Marketing API responses.
Using Pydantic for validation and type safety.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from enum import Enum


class CampaignStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class AdSetStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class AdStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    DISAPPROVED = "DISAPPROVED"
    WITH_ISSUES = "WITH_ISSUES"


@dataclass
class Campaign:
    """Represents a Meta ad campaign."""
    id: str
    name: str
    status: str
    objective: Optional[str] = None
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    created_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None


@dataclass
class AdSet:
    """Represents a Meta ad set."""
    id: str
    name: str
    status: str
    campaign_id: str
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    targeting: Optional[dict] = None
    optimization_goal: Optional[str] = None
    billing_event: Optional[str] = None
    created_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class Ad:
    """Represents a Meta ad."""
    id: str
    name: str
    status: str
    adset_id: str
    campaign_id: Optional[str] = None
    creative_id: Optional[str] = None
    created_time: Optional[datetime] = None
    # Creative content (populated separately)
    primary_text: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    call_to_action_type: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    creative_format: Optional[str] = None  # e.g. "carousel (2 images)", "single image", "video"


@dataclass
class Insights:
    """Performance metrics for a campaign, ad set, or ad."""
    entity_id: str
    entity_type: str  # 'campaign', 'adset', 'ad'
    date_start: date
    date_stop: date

    # Spend metrics
    spend: float = 0.0

    # Reach metrics
    impressions: int = 0
    reach: int = 0
    frequency: float = 0.0

    # Engagement metrics
    clicks: int = 0
    link_clicks: int = 0
    ctr: float = 0.0  # Click-through rate (%)

    # Cost metrics
    cpm: float = 0.0  # Cost per 1000 impressions
    cpc: float = 0.0  # Cost per click

    # Conversion metrics
    leads: int = 0
    cost_per_lead: float = 0.0
    messages: int = 0
    cost_per_message: float = 0.0
    landing_page_views: int = 0

    # Other
    conversions: int = 0
    conversion_value: float = 0.0

    def __post_init__(self):
        """Calculate derived metrics if needed."""
        # Calculate CTR if we have impressions and clicks
        if self.impressions > 0 and self.ctr == 0.0:
            self.ctr = (self.clicks / self.impressions) * 100

        # Calculate CPM if we have spend and impressions
        if self.impressions > 0 and self.cpm == 0.0:
            self.cpm = (self.spend / self.impressions) * 1000

        # Calculate CPC if we have spend and clicks
        if self.clicks > 0 and self.cpc == 0.0:
            self.cpc = self.spend / self.clicks

        # Calculate cost per lead if we have leads
        if self.leads > 0 and self.cost_per_lead == 0.0:
            self.cost_per_lead = self.spend / self.leads


@dataclass
class GeoInsights:
    """Geographic performance breakdown."""
    entity_id: str
    date_start: date
    date_stop: date
    region: str
    city: Optional[str] = None
    country: str = "US"

    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    cost_per_lead: float = 0.0
    ctr: float = 0.0


@dataclass
class PerformanceSnapshot:
    """A point-in-time snapshot of entity performance."""
    entity_id: str
    entity_type: str
    entity_name: str
    snapshot_date: date

    # Key metrics
    spend: float
    impressions: int
    clicks: int
    leads: int
    cost_per_lead: float
    ctr: float
    cpm: float
    frequency: float

    # Calculated scores
    performance_score: float = 0.0  # 0-100
    trend: str = "stable"  # "improving", "declining", "stable"
    flags: list = field(default_factory=list)  # ["high_cpl", "low_ctr", etc.]
