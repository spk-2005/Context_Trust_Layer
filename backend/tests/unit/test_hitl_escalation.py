import uuid
from datetime import datetime, timezone
import pytest

from app.db.models.hitl_escalation import HitlEscalation
from app.schemas.decision import DecisionActor, DecisionEvaluateRequest, DecisionEvaluateResponse
from app.schemas.hitl import HitlResolveRequest
from app.services.hitl_service import (
    _IN_MEMORY_ESCALATIONS,
    _seed_sample_escalations_if_empty,
    record_hitl_escalation_if_needed,
)


@pytest.mark.asyncio
async def test_hitl_escalation_skipped_for_allow():
    req = DecisionEvaluateRequest(
        decision="Check inventory for standard item #101",
        actor=DecisionActor(id="test-agent", role="catalog_reader"),
    )
    decision = DecisionEvaluateResponse(
        decision="ALLOW",
        validity="VALID",
        risk="LOW",
        reasons=[],
        audit_id="audit-123",
        suggested_action=None,
        audit_token="audit-allow-test-123",
        execution_ms=12,
    )
    res = await record_hitl_escalation_if_needed(req, decision, uuid.uuid4(), "audit-123")
    assert res is None


@pytest.mark.asyncio
async def test_hitl_escalation_created_for_review():
    org_id = uuid.uuid4()
    req = DecisionEvaluateRequest(
        decision="Refund $3,200 payment for customer dispute ticket #441",
        actor=DecisionActor(id="billing-bot", role="billing_agent"),
        organization_id=org_id,
    )
    decision = DecisionEvaluateResponse(
        decision="REVIEW",
        validity="INSUFFICIENT",
        risk="HIGH",
        reasons=["Dual custody rule requires secondary signoff on refund > $2,500"],
        audit_id="audit-456",
        suggested_action="Escalate to finance supervisor",
        audit_token="audit-token-456",
        execution_ms=25,
    )
    escalation = await record_hitl_escalation_if_needed(req, decision, org_id, "audit-456")
    assert escalation is not None
    assert escalation.status == "PENDING"
    assert escalation.actor_id == "billing-bot"
    assert escalation.actor_role == "billing_agent"
    assert escalation.category == "Financial & Rogue Transactions"
    assert escalation.liability_prevented_usd == 3200.0
    assert str(escalation.id) in _IN_MEMORY_ESCALATIONS


def test_seed_sample_escalations():
    org_id = uuid.uuid4()
    _seed_sample_escalations_if_empty(org_id)
    org_items = [e for e in _IN_MEMORY_ESCALATIONS.values() if e.organization_id == org_id]
    assert len(org_items) >= 2
    statuses = {e.status for e in org_items}
    assert "PENDING" in statuses


def test_hitl_model_attributes():
    org_id = uuid.uuid4()
    esc = HitlEscalation(
        organization_id=org_id,
        audit_id="audit-test-999",
        actor_id="agent-007",
        actor_role="compliance_officer",
        action_prompt="Modify data retention policy to 1 year",
        reasons=["Requires CISO sign-off"],
        category="Regulatory & Contractual SLA",
        liability_prevented_usd=15000.0,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    assert esc.category == "Regulatory & Contractual SLA"
    assert esc.liability_prevented_usd == 15000.0
    assert esc.status == "PENDING"
