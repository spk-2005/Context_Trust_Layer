import decimal
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.enums import ClaimStatus


class ClaimEvidenceResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    document_id: uuid.UUID
    evidence_type: str
    page_number: int | None = None
    section: str | None = None
    text_span: str
    start_offset: int | None = None
    end_offset: int | None = None
    evidence_hash: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimValidityResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    version: str | None = None
    is_current: bool
    validity_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimTrustScoreResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    source_score: decimal.Decimal
    freshness_score: decimal.Decimal
    evidence_score: decimal.Decimal
    consistency_score: decimal.Decimal
    authority_score: decimal.Decimal
    human_score: decimal.Decimal
    overall_score: decimal.Decimal
    scoring_model: str | None = None
    scoring_version: str | None = None
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    document_version_id: uuid.UUID
    claim_text: str
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    claim_type: str | None = None
    extraction_method: str | None = None
    extraction_model: str | None = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    evidence: list[ClaimEvidenceResponse] = []
    validity_records: list[ClaimValidityResponse] = []
    trust_scores: list[ClaimTrustScoreResponse] = []

    model_config = ConfigDict(from_attributes=True)
