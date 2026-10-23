"""
Configurable Risk Policy and Retrieval Access Gate.

Enforces retrieval and execution gates based on organization risk policy,
certification tier, claim type, and agent intent.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.universal_claim import ClaimLifecycleState, ClaimType, UniversalClaim


class AgentAccessDecision(str, Enum):
    FULL_AUTONOMOUS = "FULL_AUTONOMOUS"
    CITATION_ONLY = "CITATION_ONLY"
    HUMAN_CONFIRMATION_REQUIRED = "HUMAN_CONFIRMATION_REQUIRED"
    BLOCKED = "BLOCKED"


class RiskPolicyConfig(BaseModel):
    organization_id: Optional[str] = None
    document_type: Optional[str] = None
    high_risk_predicates: List[str] = Field(
        default_factory=lambda: [
            "may_terminate_without_cause",
            "may_terminate_for_material_breach_on_30_days_notice",
            "must_not_compete",
            "has_liability_cap",
            "may_suspend_for_security_or_breach",
            "indemnify",
            "accept_liability",
            "issue_refund",
            "share_personal_data",
            "make_legal_commitment",
        ]
    )
    autonomous_allowed_actions: List[str] = Field(
        default_factory=lambda: [
            "answer_policy_question",
            "cite_clause",
            "explain_condition",
            "refuse_unstated",
            "read_context",
        ]
    )
    human_confirmation_required_for_high_risk: bool = True


class RiskPolicyEvaluator:
    """Evaluates agent access requests against claim certification and risk policy."""

    @classmethod
    def evaluate_access(
        cls,
        claim: UniversalClaim,
        proposed_action: str = "read_context",
        policy: Optional[RiskPolicyConfig] = None,
    ) -> tuple[AgentAccessDecision, str]:
        if policy is None:
            policy = RiskPolicyConfig()

        # 1. Blocked: Quarantined, rejected, or duplicate claims are strictly blocked from normative use
        if (
            claim.lifecycle_state in {ClaimLifecycleState.QUARANTINED, ClaimLifecycleState.REJECTED, ClaimLifecycleState.DUPLICATE}
            or claim.certification_tier in {"QUARANTINED", "REJECTED", "DUPLICATE"}
        ):
            return (
                AgentAccessDecision.BLOCKED,
                f"Claim is {claim.lifecycle_state.value}; quarantined or rejected propositions cannot be retrieved for decision-making.",
            )

        # 2. Citation Only: Non-rule claims (definitions, references, descriptions)
        if claim.claim_type != ClaimType.RULE or claim.certification_tier == "NON_RULE":
            return (
                AgentAccessDecision.CITATION_ONLY,
                f"Claim is a non-rule ({claim.claim_type.value}); available for informational citation only, not autonomous normative enforcement.",
            )

        # 3. Uncertified / Review Required claims
        if claim.certification_tier != "AUTOMATED_CERTIFIED" and claim.lifecycle_state != ClaimLifecycleState.AUTOMATED_CERTIFIED:
            return (
                AgentAccessDecision.HUMAN_CONFIRMATION_REQUIRED,
                "Claim is in REVIEW_REQUIRED tier; requires human adjudication before autonomous action.",
            )

        # 4. High-risk action verification
        action_lower = proposed_action.lower()
        pred_action = claim.predicate.normalized_action.lower()

        is_high_risk_predicate = pred_action in [p.lower() for p in policy.high_risk_predicates]
        is_write_action = action_lower not in [a.lower() for a in policy.autonomous_allowed_actions]

        if is_high_risk_predicate and is_write_action and policy.human_confirmation_required_for_high_risk:
            return (
                AgentAccessDecision.HUMAN_CONFIRMATION_REQUIRED,
                f"Action '{proposed_action}' involves high-risk predicate '{pred_action}'; human confirmation required by policy.",
            )

        # 5. Full Autonomous: Verified canonical rule with authorized action
        return (
            AgentAccessDecision.FULL_AUTONOMOUS,
            "Claim is fully certified and authorized for autonomous agent decision-making.",
        )
