import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.mcp_middleware import (
    ToolCallProposal,
    ToolInterceptionResult,
    ToolRiskTier,
    WorkflowPlanEvaluateRequest,
    WorkflowPlanEvaluateResponse,
)
from app.services.webhook_service import compute_single_incident_liability

logger = logging.getLogger(__name__)

# Heuristic patterns for SQL & Shell Injection in tool arguments
SQL_INJECTION_PATTERNS = [
    r"\b(drop|truncate|alter)\s+(table|database|schema)?\s*[a-zA-Z0-9_]+",
    r"\bdelete\s+from\b",
    r";\s*(drop|delete|insert|update|truncate)\b",
    r"(\bunion\s+select\b|\bselect\s+.*\s+from\s+information_schema\b)",
    r"(\bor\s+1=1\b|--|#\s*$)",
]

SHELL_INJECTION_PATTERNS = [
    r"\b(rm\s+-rf|rmdir|mkfs)\b",
    r"\b(cat\s+/etc/shadow|cat\s+/etc/passwd)\b",
    r"(\|\s*bash|\|\s*sh|curl.*\|\s*sh)",
    r"\b(whoami|chmod\s+777|chown\s+root)\b",
    r"\b(iptables\s+-F|ufw\s+disable)\b",
]


def classify_tool_tier(tool_name: str) -> ToolRiskTier:
    """Classifies tool into risk tiers based on tool name semantics."""
    t_lower = (tool_name or "").lower()

    # Tier 4 Dangerous
    if any(k in t_lower for k in [
        "shell", "bash", "terminal", "drop", "truncate", "kill",
        "wire_transfer", "crypto_payout", "firewall", "reboot", "shutdown",
        "delete_database", "iam_role_grant", "shell_exec", "run_cmd"
    ]):
        return ToolRiskTier.TIER_4_DANGEROUS

    # Tier 3 High Mutation
    if any(k in t_lower for k in [
        "sql", "database", "refund", "update", "delete", "modify", "patch",
        "send_payment", "change_policy", "grant_leave", "set_contract", "execute"
    ]):
        return ToolRiskTier.TIER_3_MUTATING_HIGH

    # Tier 2 Low Mutation
    if any(k in t_lower for k in [
        "add_comment", "tag", "draft", "note", "notify", "send_email",
        "create_ticket", "append", "log"
    ]):
        return ToolRiskTier.TIER_2_MUTATING_LOW

    # Tier 1 Read Only
    return ToolRiskTier.TIER_1_READ_ONLY


def scan_arguments_for_threats(arguments: Dict[str, Any]) -> List[str]:
    """Inspects all string argument values recursively for SQL, shell, or exfiltration indicators."""
    threats = []
    args_json = json.dumps(arguments).lower()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, args_json, re.IGNORECASE):
            threats.append(f"SQL Injection signature detected: {pattern}")
            break

    for pattern in SHELL_INJECTION_PATTERNS:
        if re.search(pattern, args_json, re.IGNORECASE):
            threats.append(f"Critical Shell / Command Injection signature detected: {pattern}")
            break

    return threats


async def intercept_tool_call(
    proposal: ToolCallProposal,
) -> ToolInterceptionResult:
    """Interprets and enforces safety governance policies on a planned tool invocation before execution."""
    t0 = time.perf_counter()
    tier = classify_tool_tier(proposal.tool_name)
    reasons: List[str] = []
    liability_prevented = 0.0
    suggested_action = None
    role_lower = (proposal.actor_role or "support").lower()

    # 1. Scan argument payloads for malicious injection patterns
    threats = scan_arguments_for_threats(proposal.arguments)
    if threats:
        tier = ToolRiskTier.TIER_4_DANGEROUS
        reasons.extend(threats)
        reasons.append("Tool execution immediately halted by Deterministic Security Policy.")
        verdict = "BLOCK"
        liability_prevented = 45000.0
        suggested_action = "Reject tool call and flag security incident for anomalous prompt execution."
    else:
        # 2. Check Role-Based Tool Entitlements & Thresholds
        if tier == ToolRiskTier.TIER_4_DANGEROUS:
            if role_lower not in ("admin", "ciso", "lead_devops"):
                verdict = "BLOCK"
                reasons.append(
                    f"Separation of Duties Violation: Role '{proposal.actor_role}' is not authorized to invoke dangerous tool '{proposal.tool_name}'."
                )
                liability_prevented = 50000.0
                suggested_action = "Require manual C-level or CISO approval before re-attempting dangerous operation."
            else:
                verdict = "REQUIRE_REVIEW"
                reasons.append("High-impact dangerous tool requires mandatory dual-custody verification under EU AI Act Art. 14.")
                liability_prevented = 25000.0
                suggested_action = "Route to Human-in-the-Loop review queue for auditor sign-off."

        elif tier == ToolRiskTier.TIER_3_MUTATING_HIGH:
            # Check for financial refund thresholds
            amount = 0.0
            for k, v in proposal.arguments.items():
                if "amount" in k.lower() or "refund" in k.lower() or "price" in k.lower():
                    try:
                        amount = float(v)
                    except (ValueError, TypeError):
                        pass

            if amount > 2500.0 and role_lower not in ("finance", "admin"):
                verdict = "REQUIRE_REVIEW"
                reasons.append(
                    f"Financial Safety Ceiling: Transaction amount ${amount:,.2f} exceeds automated limit ($2,500.00) for role '{proposal.actor_role}'."
                )
                liability_prevented = amount
                suggested_action = "Escalate to finance supervisor for dual sign-off."
            elif "delete" in proposal.tool_name.lower() and role_lower not in ("admin", "data_owner"):
                verdict = "BLOCK"
                reasons.append(f"Destructive mutation '{proposal.tool_name}' blocked for role '{proposal.actor_role}'.")
                liability_prevented = 10000.0
                suggested_action = "Contact Data Owner for authorized data pruning."
            else:
                verdict = "PERMIT"
                reasons.append("Tool invocation complies with deterministic role policy bounds.")

        elif tier == ToolRiskTier.TIER_2_MUTATING_LOW:
            verdict = "PERMIT"
            reasons.append("Low-mutation tool call authorized with standard execution telemetry.")

        else:
            # TIER_1_READ_ONLY
            verdict = "PERMIT"
            reasons.append("Read-only context lookup granted.")

    # Calculate risk score
    tier_scores = {
        ToolRiskTier.TIER_1_READ_ONLY: 10.0,
        ToolRiskTier.TIER_2_MUTATING_LOW: 35.0,
        ToolRiskTier.TIER_3_MUTATING_HIGH: 70.0,
        ToolRiskTier.TIER_4_DANGEROUS: 95.0,
    }
    risk_score = tier_scores[tier]
    if verdict == "BLOCK":
        risk_score = max(risk_score, 90.0)

    # Cryptographic permit token generation
    permit_token = None
    if verdict in ("PERMIT", "SANITIZE_AND_PERMIT"):
        payload_bytes = f"{proposal.tool_name}:{proposal.actor_id}:{time.time()}".encode("utf-8")
        permit_token = f"permit_{hashlib.sha256(payload_bytes).hexdigest()[:24]}"

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return ToolInterceptionResult(
        verdict=verdict,
        permit_token=permit_token,
        risk_tier=tier,
        risk_score=risk_score,
        reasons=reasons,
        sanitized_arguments=proposal.arguments,
        liability_prevented_usd=liability_prevented,
        suggested_action=suggested_action,
        execution_ms=duration_ms,
        timestamp=datetime.now(timezone.utc),
    )


async def evaluate_workflow_plan(
    plan: WorkflowPlanEvaluateRequest,
) -> WorkflowPlanEvaluateResponse:
    """Pre-audits an entire multi-step agent workflow plan before any tool execution begins."""
    step_evals: List[ToolInterceptionResult] = []
    total_liability = 0.0
    accumulated_risk = 0.0
    all_reasons: List[str] = []
    highest_tier = ToolRiskTier.TIER_1_READ_ONLY

    tier_order = [
        ToolRiskTier.TIER_1_READ_ONLY,
        ToolRiskTier.TIER_2_MUTATING_LOW,
        ToolRiskTier.TIER_3_MUTATING_HIGH,
        ToolRiskTier.TIER_4_DANGEROUS,
    ]

    for step in plan.steps:
        proposal = ToolCallProposal(
            tool_name=step.tool_name,
            arguments=step.arguments,
            actor_id=plan.actor_id,
            actor_role=plan.actor_role,
            organization_id=plan.organization_id,
            workflow_id=plan.workflow_id,
            step_index=step.step_id,
            justification=step.description,
        )
        res = await intercept_tool_call(proposal)
        step_evals.append(res)
        total_liability += res.liability_prevented_usd
        accumulated_risk += res.risk_score

        if tier_order.index(res.risk_tier) > tier_order.index(highest_tier):
            highest_tier = res.risk_tier

        if res.verdict != "PERMIT":
            all_reasons.extend(res.reasons)

    # Determine overall workflow verdict
    if any(s.verdict == "BLOCK" for s in step_evals):
        overall_verdict = "BLOCK"
    elif any(s.verdict == "REQUIRE_REVIEW" for s in step_evals) or accumulated_risk > 150.0:
        overall_verdict = "REQUIRE_REVIEW"
        if accumulated_risk > 150.0 and "Accumulated risk" not in "".join(all_reasons):
            all_reasons.append(
                f"Multi-Step Risk Compounding: Cumulative workflow risk score ({accumulated_risk:.1f}) exceeds composite threshold."
            )
    else:
        overall_verdict = "PERMIT"
        all_reasons.append("All planned agent tool steps meet deterministic governance criteria.")

    normalized_risk = min(100.0, round(accumulated_risk / max(1, len(plan.steps)), 1))

    return WorkflowPlanEvaluateResponse(
        workflow_id=plan.workflow_id,
        verdict=overall_verdict,
        max_risk_tier=highest_tier,
        accumulated_risk_score=normalized_risk,
        total_liability_prevented_usd=total_liability,
        reasons=all_reasons,
        step_evaluations=step_evals,
    )
