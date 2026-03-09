"""
Agent Brain - LLM Integration

This module handles communication with the Claude API for reasoning
and decision-making. It's the "thinking" part of the agent.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

import anthropic

from .prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE, QUICK_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result from LLM analysis."""
    raw_response: str
    executive_summary: str
    performance_analysis: str
    copy_insights: str
    creative_insights: str
    geographic_insights: str
    recommendations: list[dict]
    tokens_used: int
    model: str


class AgentBrain:
    """
    The reasoning engine of the agent, powered by Claude.

    This class handles all LLM interactions - sending data for analysis
    and parsing the responses into structured insights.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ):
        """
        Initialize the agent brain.

        Args:
            api_key: Anthropic API key. Reads from ANTHROPIC_API_KEY env var if not provided.
            model: Claude model to use. Defaults to claude-sonnet-4-20250514 for cost efficiency.
            max_tokens: Maximum tokens in response.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Set it in .env or pass to AgentBrain()."
            )

        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=self.api_key)

        logger.info(f"AgentBrain initialized with model: {self.model}")

    def analyze(
        self,
        campaign_data: str,
        adset_data: str,
        ad_data: str,
        historical_context: str = "No historical data available yet.",
        date_range: str = "Last 7 Days"
    ) -> AnalysisResult:
        """
        Perform full analysis of ad account data.

        Args:
            campaign_data: Formatted campaign performance data
            adset_data: Formatted ad set performance data
            ad_data: Formatted ad performance data with copy/creative
            historical_context: Past decisions, outcomes, learnings
            date_range: Time period being analyzed

        Returns:
            AnalysisResult with parsed insights and recommendations
        """
        # Build the analysis prompt
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            date_range=date_range,
            campaign_data=campaign_data,
            adset_data=adset_data,
            ad_data=ad_data,
            historical_context=historical_context
        )

        logger.info("Sending data to Claude for analysis...")

        # Call Claude API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens

        logger.info(f"Analysis complete. Tokens used: {tokens_used}")

        # Parse the response into sections
        result = self._parse_analysis_response(response_text)
        result.tokens_used = tokens_used
        result.model = self.model

        return result

    def quick_analyze(self, data: str) -> str:
        """
        Perform a quick analysis for rapid insights.

        Args:
            data: Formatted data string

        Returns:
            Quick analysis as plain text
        """
        prompt = QUICK_ANALYSIS_PROMPT.format(data=data)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def reason_about(self, question: str, context: str = "") -> str:
        """
        Ask the agent to reason about a specific question.

        Args:
            question: The question to answer
            context: Additional context to provide

        Returns:
            The agent's reasoning/response
        """
        prompt = f"{context}\n\nQuestion: {question}" if context else question

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def _parse_analysis_response(self, response: str) -> AnalysisResult:
        """
        Parse the LLM response into structured sections.

        This is a simple parser that extracts sections by headers.
        """
        sections = {
            "executive_summary": "",
            "performance_analysis": "",
            "copy_insights": "",
            "creative_insights": "",
            "geographic_insights": "",
        }

        # Simple section extraction
        current_section = None
        current_content = []

        for line in response.split("\n"):
            line_lower = line.lower().strip()

            # Detect section headers
            if "executive summary" in line_lower or "summary" in line_lower and line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "executive_summary"
                current_content = []
            elif "performance analysis" in line_lower or "performance" in line_lower and line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "performance_analysis"
                current_content = []
            elif "copy insight" in line_lower and line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "copy_insights"
                current_content = []
            elif "creative insight" in line_lower and line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "creative_insights"
                current_content = []
            elif "geographic insight" in line_lower and line.startswith("#"):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = "geographic_insights"
                current_content = []
            elif current_section:
                current_content.append(line)

        # Don't forget the last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        # Extract recommendations (more complex parsing)
        recommendations = self._parse_recommendations(response)

        return AnalysisResult(
            raw_response=response,
            executive_summary=sections["executive_summary"],
            performance_analysis=sections["performance_analysis"],
            copy_insights=sections["copy_insights"],
            creative_insights=sections["creative_insights"],
            geographic_insights=sections["geographic_insights"],
            recommendations=recommendations,
            tokens_used=0,  # Set by caller
            model=""  # Set by caller
        )

    def _parse_recommendations(self, response: str) -> list[dict]:
        """
        Extract structured recommendations from the response.

        Looks for the recommendations section and parses individual actions.
        """
        recommendations = []

        # Find the recommendations section
        lines = response.split("\n")
        in_recommendations = False
        current_rec = {}

        for line in lines:
            line_lower = line.lower().strip()

            if "recommended action" in line_lower or "## 6" in line_lower:
                in_recommendations = True
                continue

            if not in_recommendations:
                continue

            # Parse recommendation fields
            if line.strip().startswith("- **Action**") or line.strip().startswith("**Action**"):
                if current_rec:
                    recommendations.append(current_rec)
                current_rec = {"action": line.split(":", 1)[-1].strip().strip("*")}
            elif "**Target**" in line:
                current_rec["target"] = line.split(":", 1)[-1].strip().strip("*")
            elif "**Reason**" in line:
                current_rec["reason"] = line.split(":", 1)[-1].strip().strip("*")
            elif "**Evidence**" in line:
                current_rec["evidence"] = line.split(":", 1)[-1].strip().strip("*")
            elif "**Confidence**" in line:
                current_rec["confidence"] = line.split(":", 1)[-1].strip().strip("*").lower()
            elif "**Risk**" in line:
                current_rec["risk"] = line.split(":", 1)[-1].strip().strip("*").lower()
            elif "**Priority**" in line:
                try:
                    current_rec["priority"] = int(line.split(":", 1)[-1].strip().strip("*")[0])
                except (ValueError, IndexError):
                    current_rec["priority"] = 5

        # Don't forget the last recommendation
        if current_rec:
            recommendations.append(current_rec)

        return recommendations
