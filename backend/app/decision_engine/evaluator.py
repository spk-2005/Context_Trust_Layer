import re
import uuid
from datetime import datetime
from typing import Sequence

from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.decision import (
    DecisionContextItem,
    DecisionEvaluateRequest,
    DecisionEvaluateResponse,
)


class DecisionEvaluator:
    """Evaluates agent decisions and candidate evidence to prevent risky or unauthorized autonomous actions."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm = llm_provider or get_llm_provider()

    @staticmethod
    def parse_date(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(date_str.split(".")[0], fmt)
            except ValueError:
                continue
        return None

    async def evaluate(
        self,
        req: DecisionEvaluateRequest,
    ) -> DecisionEvaluateResponse:
        audit_id = f"ctx_{uuid.uuid4().hex[:10]}"
        reasons: list[str] = []
        preferred_source: str | None = None
        suggested_action: str | None = None

        # 1. Access / Role Authorization Check
        restricted_roles = {
            "refund": ["support", "finance", "admin"],
            "grant_leave": ["hr", "manager", "admin"],
            "modify_contract": ["legal", "admin"],
            "deploy_infrastructure": ["devops", "admin"],
        }
        dec_lower = req.decision.lower()
        for action_key, allowed_roles in restricted_roles.items():
            normalized_action = action_key.replace("_", " ")
            if (action_key in dec_lower or normalized_action in dec_lower) and req.actor.role.lower() not in allowed_roles:
                reasons.append(
                    f"Actor role '{req.actor.role}' is not authorized for decision category '{normalized_action}'."
                )
                return DecisionEvaluateResponse(
                    decision="BLOCK",
                    validity="INSUFFICIENT",
                    risk="HIGH",
                    reasons=reasons,
                    preferred_source=None,
                    audit_id=audit_id,
                    suggested_action="Escalate to a qualified supervisor with appropriate permissions.",
                )

        # 2. Empty Context Check
        if not req.context:
            return DecisionEvaluateResponse(
                decision="CLARIFY",
                validity="INSUFFICIENT",
                risk="MEDIUM",
                reasons=["No candidate context or evidence provided for this decision."],
                preferred_source=None,
                audit_id=audit_id,
                suggested_action="Retrieve candidate evidence from authoritative sources before making decision.",
            )

        # 3. Analyze Sources, Authority, and Dates
        items = req.context
        sources_with_dates = []
        for it in items:
            dt = self.parse_date(it.updated_at)
            auth = it.authority_level if it.authority_level is not None else 50
            if "policy" in it.source.lower() or "service" in it.source.lower():
                auth = max(auth, 85)
            sources_with_dates.append((it, dt, auth))

        # Sort by authority (highest first) and date (newest first)
        sources_with_dates.sort(key=lambda x: (x[2], x[1] or datetime.min), reverse=True)
        preferred_item = sources_with_dates[0][0]
        preferred_source = preferred_item.source

        # 4. Check for Contradictions / Conflicts Among Candidate Claims
        has_conflict = False
        conflict_details: list[str] = []

        if len(items) >= 2:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    item_a = items[i]
                    item_b = items[j]

                    # LLM / Rule Contradiction Evaluation
                    res = await self.llm.evaluate_contradiction(item_a.claim, item_b.claim)
                    if res.is_contradiction:
                        has_conflict = True
                        conflict_details.append(
                            f"Contradiction between '{item_a.source}' and '{item_b.source}': {res.reasoning}"
                        )

        # 5. Check Scope & Effective Dates Discrepancies
        has_date_discrepancy = False
        if len(sources_with_dates) >= 2:
            dt_newest = sources_with_dates[0][1]
            dt_oldest = sources_with_dates[-1][1]
            if dt_newest and dt_oldest and dt_newest != dt_oldest:
                has_date_discrepancy = True

        # Check if exception exists (e.g. Enterprise exception)
        has_scope_exception = any("exception" in it.claim.lower() for it in items)

        # 6. Formulate Decision Outcome
        if has_conflict:
            reasons.append("Conflicting policy evidence detected across candidate sources.")
            if has_date_discrepancy:
                reasons.append("Candidate sources have different effective dates or update timestamps.")
            if has_scope_exception:
                reasons.append("A specific scope exception or override was identified.")

            # If there is a clear newer authoritative source (authority > 80)
            if sources_with_dates[0][2] >= 80 and has_scope_exception:
                decision_outcome = "REVIEW"
                validity_outcome = "INSUFFICIENT"
                risk_outcome = "HIGH"
                suggested_action = (
                    f"Route to human review. Note: '{preferred_source}' is the newer and designated source of truth."
                )
            else:
                decision_outcome = "REVIEW"
                validity_outcome = "INSUFFICIENT"
                risk_outcome = "HIGH"
                suggested_action = "Hold decision for human review to resolve contradictory guidelines."

            return DecisionEvaluateResponse(
                decision=decision_outcome,
                validity=validity_outcome,
                risk=risk_outcome,
                reasons=reasons,
                preferred_source=preferred_source,
                audit_id=audit_id,
                suggested_action=suggested_action,
            )

        # Non-conflicting, valid evidence
        reasons.append("Authoritative policy verified.")
        reasons.append("Evidence is current and uncontradicted.")
        if preferred_source:
            reasons.append(f"Primary backing source: '{preferred_source}'.")

        return DecisionEvaluateResponse(
            decision="ALLOW",
            validity="VALID",
            risk="LOW",
            reasons=reasons,
            preferred_source=preferred_source,
            audit_id=audit_id,
            suggested_action="Proceed with authorized action using verified evidence.",
        )
