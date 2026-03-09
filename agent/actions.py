"""
Agent Actions - Safe Action Execution

This module handles executing actions on the Meta Ads account
with safety checks and validation.
"""

import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions the agent can take."""
    PAUSE_AD = "pause_ad"
    PAUSE_ADSET = "pause_adset"
    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_AD = "enable_ad"
    ENABLE_ADSET = "enable_adset"
    REDUCE_BUDGET = "reduce_budget"
    INCREASE_BUDGET = "increase_budget"
    UPDATE_COPY = "update_copy"
    UPDATE_TARGETING = "update_targeting"
    CREATE_AD = "create_ad"


class ApprovalStatus(str, Enum):
    """Approval status for actions."""
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


@dataclass
class ActionRequest:
    """A request to take an action on the ad account."""
    action_type: ActionType
    target_type: str  # "campaign", "adset", "ad"
    target_id: str
    target_name: str
    reason: str
    confidence: str  # "high", "medium", "low"
    risk: str  # "low", "medium", "high"
    parameters: dict = None  # Additional parameters like new budget amount

    # Approval tracking
    requires_approval: bool = True
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


@dataclass
class ActionResult:
    """Result of executing an action."""
    success: bool
    action_request: ActionRequest
    executed_at: str
    error_message: Optional[str] = None
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None


# Actions that can be auto-approved (low risk)
SAFE_ACTIONS = {
    ActionType.PAUSE_AD: {
        "conditions": ["spend > 30 and messages == 0"],
        "max_per_day": 5,
    },
    ActionType.REDUCE_BUDGET: {
        "conditions": ["reduction_percent <= 10"],
        "max_per_day": 3,
    },
}

# Actions that always require human approval
REQUIRES_APPROVAL = {
    ActionType.INCREASE_BUDGET,
    ActionType.ENABLE_AD,
    ActionType.ENABLE_ADSET,
    ActionType.UPDATE_COPY,
    ActionType.UPDATE_TARGETING,
    ActionType.CREATE_AD,
}


class ActionExecutor:
    """
    Executes actions on the Meta Ads account.

    Includes safety checks to prevent dangerous actions without approval.
    """

    def __init__(self, meta_client, dry_run: bool = True):
        """
        Initialize the action executor.

        Args:
            meta_client: Meta API client for executing actions
            dry_run: If True, actions are logged but not executed
        """
        self.meta_client = meta_client
        self.dry_run = dry_run
        self.actions_today = {}  # Track actions per type for limits

        logger.info(f"ActionExecutor initialized (dry_run={dry_run})")

    def can_auto_approve(self, request: ActionRequest) -> bool:
        """
        Check if an action can be auto-approved.

        Args:
            request: The action request to check

        Returns:
            True if the action can be auto-approved
        """
        # Actions not in safe list always require approval
        if request.action_type not in SAFE_ACTIONS:
            return False

        # Check daily limits
        safe_config = SAFE_ACTIONS[request.action_type]
        count = self.actions_today.get(request.action_type, 0)
        if count >= safe_config.get("max_per_day", 10):
            logger.warning(f"Daily limit reached for {request.action_type}")
            return False

        # High risk actions always need approval
        if request.risk == "high":
            return False

        # Low confidence actions need approval
        if request.confidence == "low":
            return False

        return True

    def request_action(self, request: ActionRequest) -> ActionRequest:
        """
        Process an action request and determine if it needs approval.

        Args:
            request: The action request

        Returns:
            Updated request with approval status
        """
        if request.action_type in REQUIRES_APPROVAL:
            request.requires_approval = True
            request.approval_status = ApprovalStatus.PENDING
            logger.info(f"Action {request.action_type} on {request.target_name} requires approval")
        elif self.can_auto_approve(request):
            request.requires_approval = False
            request.approval_status = ApprovalStatus.AUTO_APPROVED
            logger.info(f"Action {request.action_type} on {request.target_name} auto-approved")
        else:
            request.requires_approval = True
            request.approval_status = ApprovalStatus.PENDING
            logger.info(f"Action {request.action_type} on {request.target_name} needs approval")

        return request

    def execute(self, request: ActionRequest) -> ActionResult:
        """
        Execute an approved action.

        Args:
            request: The action request to execute

        Returns:
            ActionResult with success status and details
        """
        # Check approval
        if request.approval_status not in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED]:
            return ActionResult(
                success=False,
                action_request=request,
                executed_at=datetime.now().isoformat(),
                error_message="Action not approved"
            )

        # Dry run mode - log but don't execute
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {request.action_type} on {request.target_name}")
            return ActionResult(
                success=True,
                action_request=request,
                executed_at=datetime.now().isoformat(),
                error_message="Dry run - action not actually executed"
            )

        # Execute the action
        try:
            before_state = self._get_entity_state(request.target_type, request.target_id)

            if request.action_type == ActionType.PAUSE_AD:
                self._pause_ad(request.target_id)
            elif request.action_type == ActionType.PAUSE_ADSET:
                self._pause_adset(request.target_id)
            elif request.action_type == ActionType.PAUSE_CAMPAIGN:
                self._pause_campaign(request.target_id)
            elif request.action_type == ActionType.REDUCE_BUDGET:
                self._reduce_budget(request.target_type, request.target_id, request.parameters)
            else:
                return ActionResult(
                    success=False,
                    action_request=request,
                    executed_at=datetime.now().isoformat(),
                    error_message=f"Action type {request.action_type} not implemented"
                )

            after_state = self._get_entity_state(request.target_type, request.target_id)

            # Track action for daily limits
            self.actions_today[request.action_type] = self.actions_today.get(request.action_type, 0) + 1

            logger.info(f"Successfully executed: {request.action_type} on {request.target_name}")

            return ActionResult(
                success=True,
                action_request=request,
                executed_at=datetime.now().isoformat(),
                before_state=before_state,
                after_state=after_state
            )

        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            return ActionResult(
                success=False,
                action_request=request,
                executed_at=datetime.now().isoformat(),
                error_message=str(e)
            )

    def approve(self, request: ActionRequest, approved_by: str = "human") -> ActionRequest:
        """
        Approve an action for execution.

        Args:
            request: The action request to approve
            approved_by: Who approved the action

        Returns:
            Updated request with approval status
        """
        request.approval_status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now().isoformat()
        logger.info(f"Action approved by {approved_by}: {request.action_type} on {request.target_name}")
        return request

    def reject(self, request: ActionRequest, reason: str = "") -> ActionRequest:
        """
        Reject an action request.

        Args:
            request: The action request to reject
            reason: Why the action was rejected

        Returns:
            Updated request with rejection status
        """
        request.approval_status = ApprovalStatus.REJECTED
        logger.info(f"Action rejected: {request.action_type} on {request.target_name}. Reason: {reason}")
        return request

    def _get_entity_state(self, target_type: str, target_id: str) -> dict:
        """Get the current state of an entity for before/after comparison."""
        # TODO: Implement actual state fetching from Meta API
        return {"status": "unknown", "id": target_id}

    def _pause_ad(self, ad_id: str):
        """Pause an ad."""
        # TODO: Implement via Meta API
        # self.meta_client.update_ad_status(ad_id, "PAUSED")
        logger.info(f"Paused ad: {ad_id}")

    def _pause_adset(self, adset_id: str):
        """Pause an ad set."""
        # TODO: Implement via Meta API
        logger.info(f"Paused ad set: {adset_id}")

    def _pause_campaign(self, campaign_id: str):
        """Pause a campaign."""
        # TODO: Implement via Meta API
        logger.info(f"Paused campaign: {campaign_id}")

    def _reduce_budget(self, target_type: str, target_id: str, params: dict):
        """Reduce budget for a campaign or ad set."""
        # TODO: Implement via Meta API
        reduction = params.get("reduction_percent", 10)
        logger.info(f"Reduced budget by {reduction}% for {target_type} {target_id}")
