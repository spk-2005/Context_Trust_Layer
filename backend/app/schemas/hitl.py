from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class HitlEscalationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    audit_id: str
    actor_id: str
    actor_role: str
    action_prompt: str
    reasons: List[str] = Field(default_factory=list)
    category: str = "Operational Triage"
    liability_prevented_usd: float = 0.0
    status: str = "PENDING"  # "PENDING" | "APPROVED" | "REJECTED"
    suggested_action: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolved_by_role: Optional[str] = None
    resolution_decision: Optional[str] = None  # "APPROVE" | "REJECT"
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HitlResolveRequest(BaseModel):
    decision: str = Field(..., description="'APPROVE' (override & proceed) or 'REJECT' (block action)")
    notes: Optional[str] = Field(None, description="Auditor justification and sign-off rationale")
    suggested_action: Optional[str] = Field(None, description="Corrective action recommendation or instructions")


class HitlSummaryResponse(BaseModel):
    total_count: int
    pending_count: int
    approved_count: int
    rejected_count: int
    total_liability_prevented_usd: float
    eu_act_compliance_rate: float
