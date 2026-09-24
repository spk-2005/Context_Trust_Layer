import decimal
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.enums import ConflictStatus, ReviewDecision
from app.schemas.claim import ClaimResponse


class ConflictResolveRequest(BaseModel):
    reviewer_id: uuid.UUID
    decision: ReviewDecision
    chosen_claim_id: uuid.UUID | None = None
    reason: str | None = None


class ConflictResponse(BaseModel):
    id: uuid.UUID
    claim_a_id: uuid.UUID
    claim_b_id: uuid.UUID
    conflict_type: str
    severity: str
    confidence: decimal.Decimal
    resolution_status: ConflictStatus
    resolved_claim_id: uuid.UUID | None = None
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    claim_a: ClaimResponse | None = None
    claim_b: ClaimResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ConflictClusterSide(BaseModel):
    representative_claim_id: uuid.UUID
    representative_text: str
    source_title: str
    section: str | None = None
    trust_score: float
    claim_count: int
    claim_ids: list[uuid.UUID]


class ConflictIssueResponse(BaseModel):
    issue_id: str
    topic: str
    conflict_type: str
    severity: str
    confidence: float
    impact_score: float = 0.0
    blast_radius: str = "ROUTINE"
    cluster_a: ConflictClusterSide
    cluster_b: ConflictClusterSide
    conflict_ids: list[uuid.UUID]
    total_conflicts: int
    created_at: datetime


class ResolveIssueRequest(BaseModel):
    reviewer_id: uuid.UUID
    decision: ReviewDecision
    chosen_side: str  # "A", "B", or "DISMISS"
    reason: str | None = None

