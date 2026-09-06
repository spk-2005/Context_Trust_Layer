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
