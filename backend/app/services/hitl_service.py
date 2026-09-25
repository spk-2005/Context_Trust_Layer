import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models.hitl_escalation import HitlEscalation
from app.schemas.decision import DecisionEvaluateRequest, DecisionEvaluateResponse
from app.services.webhook_service import compute_single_incident_liability

logger = logging.getLogger(__name__)

# Resilient in-memory store for HITL escalations when DB connection is offline
_IN_MEMORY_ESCALATIONS: Dict[str, HitlEscalation] = {}


def _seed_sample_escalations_if_empty(org_id: uuid.UUID):
    """Pre-seeds realistic pending escalations for demos and auditor review."""
    org_key = str(org_id)
    existing = [e for e in _IN_MEMORY_ESCALATIONS.values() if str(e.organization_id) == org_key]
    if not existing:
        esc_1 = HitlEscalation(
            id=uuid.UUID("44444444-4444-4444-4444-444444444441"),
            organization_id=org_id,
            audit_id="audit-review-8821",
            actor_id="autonomous-hr-agent",
            actor_role="hr_agent_bot",
            action_prompt="Update remote work policy stipend eligibility from 90 days to day 1 for international contractors.",
            reasons=[
                "Conflicting Policy: Corporate HR 2026 handbook requires 90-day probationary period for foreign currency stipends.",
                "EU AI Act Article 14 flag: High-impact contractual modification requires explicit human sign-off."
            ],
            category="Regulatory & Contractual SLA",
            liability_prevented_usd=15000.0,
            status="PENDING",
            suggested_action="Request CCO / Lead HR Business Partner sign-off before committing policy update to context store.",
            created_at=datetime.now(timezone.utc),
        )
        esc_2 = HitlEscalation(
            id=uuid.UUID("44444444-4444-4444-4444-444444444442"),
            organization_id=org_id,
            audit_id="audit-review-8822",
            actor_id="billing-service-agent",
            actor_role="billing_agent",
            action_prompt="Issue unverified wire refund of $4,850.00 for enterprise customer invoice #9921.",
            reasons=[
                "Financial Safety Guardrail: Dual-custody approval mandatory for outbound refunds exceeding $2,500.00.",
                "High Risk Level: Potential rogue automated transaction intercepted."
            ],
            category="Financial & Rogue Transactions",
            liability_prevented_usd=4850.0,
            status="PENDING",
            suggested_action="Review banking remittance details and verify against verified CRM billing agreement.",
            created_at=datetime.now(timezone.utc),
        )
        _IN_MEMORY_ESCALATIONS[str(esc_1.id)] = esc_1
        _IN_MEMORY_ESCALATIONS[str(esc_2.id)] = esc_2


async def record_hitl_escalation_if_needed(
    req: DecisionEvaluateRequest,
    decision: DecisionEvaluateResponse,
    organization_id: uuid.UUID,
    audit_id: str,
) -> Optional[HitlEscalation]:
    """Creates a new HITL escalation item if the decision returned REVIEW or REQUIRE_REVIEW."""
    verdict = (decision.verdict or "ALLOW").upper()
    if verdict not in ("REVIEW", "REQUIRE_REVIEW"):
        return None

    liability_val, category = compute_single_incident_liability(
        req.decision_prompt, req.actor.role, verdict
    )

    esc_id = uuid.uuid4()
    escalation = HitlEscalation(
        id=esc_id,
        organization_id=organization_id,
        audit_id=audit_id,
        actor_id=req.actor.id,
        actor_role=req.actor.role,
        action_prompt=req.decision_prompt,
        reasons=decision.reasons or ["Action requires human verification prior to release."],
        category=category,
        liability_prevented_usd=liability_val,
        status="PENDING",
        suggested_action=decision.suggested_action or "Review agent proposal and authorize override or permanent block.",
        created_at=datetime.now(timezone.utc),
    )

    # Store in-memory
    _IN_MEMORY_ESCALATIONS[str(esc_id)] = escalation

    # Attempt to persist to database if available
    try:
        async with AsyncSessionLocal() as session:
            session.add(escalation)
            await session.commit()
            await session.refresh(escalation)
    except Exception as e:
        logger.debug(f"Database unavailable for HITL escalation save, using in-memory store: {e}")

    return escalation
