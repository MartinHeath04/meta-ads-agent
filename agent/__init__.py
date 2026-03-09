"""
Sea Street Detailing Meta Ads Agent

A TRUE AI AGENT that uses Claude as its reasoning engine to analyze
Meta/Facebook ad performance and make intelligent recommendations.
"""

from .core import MetaAdsAgent
from .brain import AgentBrain
from .memory import AgentMemory

__all__ = ["MetaAdsAgent", "AgentBrain", "AgentMemory"]
