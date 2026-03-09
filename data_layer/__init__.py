"""
Data Layer - Meta API Client and Data Models

This module handles all data fetching from the Meta Marketing API
and structures it for the agent.
"""

from .meta_client import MetaAPIClient
from .models import Campaign, AdSet, Ad, Insights
from .context_builder import ContextBuilder

__all__ = ["MetaAPIClient", "Campaign", "AdSet", "Ad", "Insights", "ContextBuilder"]
