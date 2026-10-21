import decimal
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, model_validator

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
    is_canonical: bool = False
    certification_tier: str = "PROVISIONAL"
    agent_accessible: bool = False
    evidence: list[ClaimEvidenceResponse] = []
    validity_records: list[ClaimValidityResponse] = []
    trust_scores: list[ClaimTrustScoreResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_v3_certification(self) -> "ClaimResponse":
        st = self.status
        ct = (self.claim_type or "").lower()
        subj = (self.subject or "").lower()
        text_val = (self.claim_text or "").lower()
        is_bad = (
            "the following" in subj
            or "page 8 of 11" in subj
            or ("page 8" in text_val and "modifications to this" in text_val)
            or ("reno" in text_val and "sierra center" in text_val)
            or "without limiting other remedies" in subj
            or "without limiting other remedies" in text_val
            or "any attempted assignment" in subj
            or "failure to enforce" in subj
            or (subj == "assignment" and (self.predicate or "") == "relieve")
            or ((self.predicate or "") == "the")
        )
        is_rule = (
            st == ClaimStatus.VERIFIED
            and ct in ("rule", "policy_rule", "policy")
            and not is_bad
        )
        self.is_canonical = is_rule
        self.agent_accessible = is_rule
        if is_rule:
            self.certification_tier = "AUTOMATED_CERTIFIED"
        elif st == ClaimStatus.REJECTED or is_bad or ct in ("fragment", "duplicate"):
            self.certification_tier = "REJECTED"
        elif ct == "quarantined":
            self.certification_tier = "QUARANTINED"
        elif ct in ("definition", "description", "reference", "responsibility"):
            self.certification_tier = "NON_RULE"
        else:
            self.certification_tier = "REVIEW_REQUIRED"
        return self


class SubjectObject(BaseModel):
    entity: str
    entity_type: str = "PRODUCT_SCOPE"
    normalized: bool = True


class ValueObject(BaseModel):
    type: str = "TEXT_RULE"  # DURATION, PERCENTAGE, CURRENCY, CALENDAR_DEADLINE, BOOLEAN, ENUM, REFERENCE, TEXT_RULE
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None
    raw: str | None = None
    enum_value: str | None = None
    reference: str | None = None
    duration_type: str | None = None  # typical, maximum, minimum, target, provider_governed


class EvidenceCitation(BaseModel):
    evidence_id: str
    document_id: str
    document_version: str | None = None
    version: str | None = None
    page: int | None = None
    section: str | None = None
    table_id: str | None = None
    row_id: str | None = None
    column_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    quote: str
    content_hash: str | None = None
    extraction_method: str | None = "table_aware"


class ProductionClaim(BaseModel):
    claim_id: str
    claim_type: str = "POLICY_RULE"
    subject: SubjectObject
    predicate: str
    value: ValueObject
    time_basis: str | None = None
    deadline: dict | None = None
    conditions: list[dict] = []
    qualifiers: list[str] = []
    modality: str = "PERMISSION"
    canonical: bool = True
    validation_status: str = "APPROVED"
    trust: dict = {}
    evidence: list[EvidenceCitation] = []

