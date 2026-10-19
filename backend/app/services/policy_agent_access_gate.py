"""
Policy Answer Agent Access Gate Service.
Enforces Sprint AE-3 Quality Gate: AI Agents can access ONLY certified tiers:
- DUAL_HUMAN_CERTIFIED: Full access
- AUTO_APPROVED_CERTIFIED: Restricted/Full access by risk tier
- HUMAN_REVIEW_REQUIRED: Strict NO ACCESS (Blocked)
- QUARANTINED_REJECTED: Strict NO ACCESS (Blocked)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CertificationTier(str, Enum):
    DUAL_HUMAN_CERTIFIED = "DUAL_HUMAN_CERTIFIED"
    AUTO_APPROVED_CERTIFIED = "AUTO_APPROVED_CERTIFIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    QUARANTINED_REJECTED = "QUARANTINED_REJECTED"


class AgentAccessLevel(str, Enum):
    FULL_ACCESS = "FULL_ACCESS"
    RESTRICTED_ACCESS = "RESTRICTED_ACCESS"
    NO_ACCESS = "NO_ACCESS"


class PolicyAgentAccessGate:
    """Trust gate controlling AI agent context injection and retrieval."""

    ALLOWED_AGENT_STATES = {
        CertificationTier.DUAL_HUMAN_CERTIFIED,
        CertificationTier.AUTO_APPROVED_CERTIFIED
    }

    BLOCKED_AGENT_STATES = {
        CertificationTier.HUMAN_REVIEW_REQUIRED,
        CertificationTier.QUARANTINED_REJECTED
    }

    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []

    def check_access(
        self,
        claim: Dict[str, Any],
        agent_id: Optional[str] = None,
        agent_role: str = "policy_answer_agent",
        query_intent: Optional[str] = None
    ) -> Tuple[bool, AgentAccessLevel, str]:
        """
        Evaluate whether an AI agent is authorized to retrieve or cite a claim.
        Returns (is_allowed, access_level, reason).
        """
        cid = claim.get("candidate_id") or claim.get("id") or "unknown_claim"
        final_state = claim.get("final_state") or claim.get("certification_status") or ""

        # Map legacy or interim statuses
        if final_state in ("TIER_2_DUAL_HUMAN_ADJUDICATED", "DUAL_HUMAN_CERTIFIED"):
            resolved_state = CertificationTier.DUAL_HUMAN_CERTIFIED
        elif final_state in ("TIER_1_AUTO_VERIFIED", "AUTO_APPROVED_CERTIFIED"):
            # Check if certified through sampled audit
            if claim.get("audit_certification") or claim.get("final_state") == "AUTO_APPROVED_CERTIFIED":
                resolved_state = CertificationTier.AUTO_APPROVED_CERTIFIED
            else:
                resolved_state = CertificationTier.HUMAN_REVIEW_REQUIRED
        elif "QUARANTINE" in final_state.upper() or "REJECT" in final_state.upper():
            resolved_state = CertificationTier.QUARANTINED_REJECTED
        elif "PENDING" in final_state.upper() or "REVIEW" in final_state.upper():
            resolved_state = CertificationTier.HUMAN_REVIEW_REQUIRED
        else:
            resolved_state = CertificationTier.HUMAN_REVIEW_REQUIRED

        # Enforce Gate Rules
        now_iso = datetime.now(timezone.utc).isoformat()

        if resolved_state == CertificationTier.DUAL_HUMAN_CERTIFIED:
            allowed = True
            level = AgentAccessLevel.FULL_ACCESS
            reason = "Access granted: Claim is dual-human certified with independent consensus."
        elif resolved_state == CertificationTier.AUTO_APPROVED_CERTIFIED:
            allowed = True
            level = AgentAccessLevel.RESTRICTED_ACCESS
            reason = "Access granted: Standard claim auto-approved and validated via stratified audit."
        elif resolved_state == CertificationTier.HUMAN_REVIEW_REQUIRED:
            allowed = False
            level = AgentAccessLevel.NO_ACCESS
            reason = "Access denied: Claim is awaiting human review and cannot be cited in policy answers."
        elif resolved_state == CertificationTier.QUARANTINED_REJECTED:
            allowed = False
            level = AgentAccessLevel.NO_ACCESS
            reason = "Access denied: Claim was rejected by validation gates or human review."
        else:
            allowed = False
            level = AgentAccessLevel.NO_ACCESS
            reason = "Access denied: Uncertified claim state."

        # Audit log event
        log_entry = {
            "timestamp": now_iso,
            "candidate_id": cid,
            "agent_id": agent_id or "default_policy_agent",
            "agent_role": agent_role,
            "evaluated_state": resolved_state.value,
            "decision": "PERMIT" if allowed else "BLOCK",
            "access_level": level.value,
            "reason": reason
        }
        self._audit_log.append(log_entry)

        if not allowed:
            logger.warning(f"PolicyAgentAccessGate BLOCKED claim {cid}: {reason}")
        else:
            logger.debug(f"PolicyAgentAccessGate PERMITTED claim {cid} ({level.value})")

        return allowed, level, reason

    def filter_claims_for_agent(
        self,
        claims: List[Dict[str, Any]],
        agent_id: Optional[str] = None,
        agent_role: str = "policy_answer_agent"
    ) -> List[Dict[str, Any]]:
        """Filter a list of claims so that ONLY certified claims reach the agent."""
        permitted = []
        for c in claims:
            allowed, level, _ = self.check_access(c, agent_id=agent_id, agent_role=agent_role)
            if allowed:
                enriched = dict(c)
                enriched["agent_access_level"] = level.value
                permitted.append(enriched)
        return permitted

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)
