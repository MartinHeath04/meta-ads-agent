"""
Agent Memory - Historical Decisions & Learning

This module stores and retrieves the agent's past decisions, outcomes,
and learnings to inform future recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """A decision/action recommended or taken by the agent."""
    id: Optional[int]
    timestamp: str
    action_type: str  # "recommendation", "executed", "rejected"
    target_type: str  # "campaign", "adset", "ad"
    target_id: str
    target_name: str
    action: str  # What was done/recommended
    reason: str
    confidence: str  # "high", "medium", "low"
    outcome: Optional[str] = None  # "success", "failure", "pending", "unknown"
    outcome_notes: Optional[str] = None
    human_feedback: Optional[str] = None


@dataclass
class Learning:
    """A pattern or insight learned by the agent."""
    id: Optional[int]
    timestamp: str
    pattern_type: str  # "copy", "creative", "geographic", "performance"
    pattern: str  # Description of the pattern
    evidence: str  # Data supporting the pattern
    success: bool  # Did this pattern lead to good outcomes?
    confidence: str


class AgentMemory:
    """
    Persistent memory for the agent.

    Stores decisions, outcomes, and learnings in SQLite so the agent
    can learn from past experience and avoid repeating mistakes.
    """

    def __init__(self, db_path: str = "data/sea_street.db"):
        """
        Initialize agent memory.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_tables()
        logger.info(f"AgentMemory initialized with database: {db_path}")

    def _init_tables(self):
        """Create memory tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                target_name TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence TEXT NOT NULL,
                outcome TEXT,
                outcome_notes TEXT,
                human_feedback TEXT
            )
        """)

        # Learnings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                evidence TEXT NOT NULL,
                success INTEGER NOT NULL,
                confidence TEXT NOT NULL
            )
        """)

        # Analysis history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                date_range TEXT NOT NULL,
                raw_response TEXT NOT NULL,
                executive_summary TEXT,
                tokens_used INTEGER,
                model TEXT
            )
        """)

        conn.commit()
        conn.close()

    def record_decision(self, decision: Decision) -> int:
        """
        Record a decision made by the agent.

        Args:
            decision: The decision to record

        Returns:
            ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_decisions
            (timestamp, action_type, target_type, target_id, target_name,
             action, reason, confidence, outcome, outcome_notes, human_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.timestamp or datetime.now().isoformat(),
            decision.action_type,
            decision.target_type,
            decision.target_id,
            decision.target_name,
            decision.action,
            decision.reason,
            decision.confidence,
            decision.outcome,
            decision.outcome_notes,
            decision.human_feedback
        ))

        decision_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded decision {decision_id}: {decision.action}")
        return decision_id

    def update_outcome(
        self,
        decision_id: int,
        outcome: str,
        notes: str = None
    ):
        """
        Update the outcome of a past decision.

        Args:
            decision_id: ID of the decision to update
            outcome: "success", "failure", "pending", "unknown"
            notes: Additional notes about the outcome
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE agent_decisions
            SET outcome = ?, outcome_notes = ?
            WHERE id = ?
        """, (outcome, notes, decision_id))

        conn.commit()
        conn.close()

        logger.info(f"Updated decision {decision_id} outcome: {outcome}")

    def add_human_feedback(self, decision_id: int, feedback: str):
        """
        Add human feedback to a decision.

        Args:
            decision_id: ID of the decision
            feedback: Human feedback text
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE agent_decisions
            SET human_feedback = ?
            WHERE id = ?
        """, (feedback, decision_id))

        conn.commit()
        conn.close()

        logger.info(f"Added human feedback to decision {decision_id}")

    def record_learning(self, learning: Learning) -> int:
        """
        Record a pattern or insight learned.

        Args:
            learning: The learning to record

        Returns:
            ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_learnings
            (timestamp, pattern_type, pattern, evidence, success, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            learning.timestamp or datetime.now().isoformat(),
            learning.pattern_type,
            learning.pattern,
            learning.evidence,
            1 if learning.success else 0,
            learning.confidence
        ))

        learning_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded learning {learning_id}: {learning.pattern[:50]}...")
        return learning_id

    def get_recent_decisions(self, limit: int = 20) -> list[Decision]:
        """
        Get recent decisions for context.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of recent decisions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, action_type, target_type, target_id,
                   target_name, action, reason, confidence, outcome,
                   outcome_notes, human_feedback
            FROM agent_decisions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        decisions = []
        for row in rows:
            decisions.append(Decision(
                id=row[0],
                timestamp=row[1],
                action_type=row[2],
                target_type=row[3],
                target_id=row[4],
                target_name=row[5],
                action=row[6],
                reason=row[7],
                confidence=row[8],
                outcome=row[9],
                outcome_notes=row[10],
                human_feedback=row[11]
            ))

        return decisions

    def get_successful_patterns(self, limit: int = 10) -> list[Learning]:
        """Get patterns that led to successful outcomes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, pattern_type, pattern, evidence, success, confidence
            FROM agent_learnings
            WHERE success = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [Learning(
            id=row[0],
            timestamp=row[1],
            pattern_type=row[2],
            pattern=row[3],
            evidence=row[4],
            success=bool(row[5]),
            confidence=row[6]
        ) for row in rows]

    def get_failed_patterns(self, limit: int = 10) -> list[Learning]:
        """Get patterns that led to failed outcomes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, pattern_type, pattern, evidence, success, confidence
            FROM agent_learnings
            WHERE success = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [Learning(
            id=row[0],
            timestamp=row[1],
            pattern_type=row[2],
            pattern=row[3],
            evidence=row[4],
            success=bool(row[5]),
            confidence=row[6]
        ) for row in rows]

    def get_context_for_analysis(self) -> str:
        """
        Build a context string from memory for the LLM.

        Returns:
            Formatted string with past decisions and learnings
        """
        recent_decisions = self.get_recent_decisions(10)
        successful = self.get_successful_patterns(5)
        failed = self.get_failed_patterns(5)

        # Format past actions
        past_actions = []
        for d in recent_decisions:
            outcome_str = f" → Outcome: {d.outcome}" if d.outcome else ""
            feedback_str = f" | Feedback: {d.human_feedback}" if d.human_feedback else ""
            past_actions.append(
                f"- [{d.timestamp[:10]}] {d.action} on {d.target_name}{outcome_str}{feedback_str}"
            )

        # Format successful patterns
        success_patterns = []
        for p in successful:
            success_patterns.append(f"- {p.pattern} (confidence: {p.confidence})")

        # Format failed patterns
        fail_patterns = []
        for p in failed:
            fail_patterns.append(f"- {p.pattern} (confidence: {p.confidence})")

        # Format human feedback
        feedback_list = [d.human_feedback for d in recent_decisions if d.human_feedback]

        context = f"""### Past Actions:
{chr(10).join(past_actions) if past_actions else "No past actions recorded yet."}

### Patterns That Worked:
{chr(10).join(success_patterns) if success_patterns else "No successful patterns recorded yet."}

### Patterns That Failed:
{chr(10).join(fail_patterns) if fail_patterns else "No failed patterns recorded yet."}

### Human Feedback:
{chr(10).join(f'- {fb}' for fb in feedback_list) if feedback_list else "No human feedback recorded yet."}"""

        return context

    def save_analysis(
        self,
        date_range: str,
        raw_response: str,
        executive_summary: str,
        tokens_used: int,
        model: str
    ):
        """Save an analysis to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_analyses
            (timestamp, date_range, raw_response, executive_summary, tokens_used, model)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            date_range,
            raw_response,
            executive_summary,
            tokens_used,
            model
        ))

        conn.commit()
        conn.close()

        logger.info("Saved analysis to history")
