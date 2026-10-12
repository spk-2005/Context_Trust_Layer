"""
Layer 6: Validation Gate & Persistence Models.
Defines dimensional evaluation results, claim lifecycle decision enums,
and gate outcome schemas matching the Trulin Architecture:
- Source Match: Pass / Fail
- Completeness: Complete / Partial
- Meaning: Supported / Uncertain
- Scope: In / Out
- Time: Current / Stale
- Authority: Authoritative / Not
- Review: Yes / No
- Claim Lifecycle Decision: Approve / Review / Reject
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceMatchStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class CompletenessStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class MeaningStatus(str, Enum):
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"
    UNSUPPORTED = "unsupported"


class ScopeStatus(str, Enum):
    IN_SCOPE = "in"
    OUT_OF_SCOPE = "out"


class TimeStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"


class AuthorityStatus(str, Enum):
    AUTHORITATIVE = "authoritative"
    NON_AUTHORITATIVE = "non_authoritative"


class ReviewStatus(str, Enum):
    NO_REVIEW_NEEDED = "no"
    REVIEW_REQUIRED = "yes"


class ClaimLifecycleDecision(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


class DimensionEvaluation(BaseModel):
    """Result for an individual evaluation dimension."""
    dimension_name: str
    status: str
    score: float = Field(ge=0.0, le=1.0, description="Normalized dimensional score")
    passed: bool
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CandidateGateEvaluation(BaseModel):
    """Complete 6-dimensional evaluation and lifecycle decision for a candidate claim."""
    candidate_id: str
    envelope_id: uuid.UUID
    asset_id: str
    claim_text: str
    subject: str = ""
    predicate: str = ""
    object_: str = Field(default="", alias="object")
    evidence_text_span: str = ""
    claim_type: str = "policy"
    modality: str = "POLICY_FACT"
    conditions: List[str] = Field(default_factory=list)
    value: Optional[Any] = None
    unit: Optional[str] = None
    scope: Dict[str, Any] = Field(default_factory=dict)
    locator: Dict[str, Any] = Field(default_factory=dict)
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    
    # 6-Dimensional Gate Evaluations
    source_match: DimensionEvaluation
    completeness: DimensionEvaluation
    meaning: DimensionEvaluation
    scope_eval: DimensionEvaluation = Field(alias="scope_eval", default=None)
    time: DimensionEvaluation
    authority: DimensionEvaluation
    review_trigger: DimensionEvaluation

    # Lifecycle Synthesis
    composite_trust_score: float = Field(ge=0.0, le=1.0)
    lifecycle_decision: ClaimLifecycleDecision
    decision_reason: str
    persisted_claim_id: Optional[uuid.UUID] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "claim_text": self.claim_text,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object_,
            "evidence_text_span": self.evidence_text_span,
            "claim_type": self.claim_type,
            "modality": self.modality,
            "conditions": self.conditions,
            "value": self.value,
            "unit": self.unit,
            "scope": self.scope,
            "locator": self.locator,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_reason": self.ambiguity_reason,
            "dimensions": {
                "source_match": self.source_match.model_dump(),
                "completeness": self.completeness.model_dump(),
                "meaning": self.meaning.model_dump(),
                "scope": (self.scope_eval or self.completeness).model_dump(),
                "time": self.time.model_dump(),
                "authority": self.authority.model_dump(),
                "review": self.review_trigger.model_dump(),
            },
            "composite_trust_score": self.composite_trust_score,
            "lifecycle_decision": self.lifecycle_decision.value,
            "decision_reason": self.decision_reason,
            "persisted_claim_id": str(self.persisted_claim_id) if self.persisted_claim_id else None,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class Layer6ValidationResult(BaseModel):
    """Aggregate summary of Layer 6 Validation Gate execution across an envelope."""
    envelope_id: uuid.UUID
    asset_id: str
    total_candidates_evaluated: int
    claims_approved: int
    claims_queued_for_review: int
    claims_rejected: int
    average_trust_score: float
    evaluations: List[CandidateGateEvaluation] = Field(default_factory=list)
    persisted_claim_ids: List[uuid.UUID] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "total_candidates_evaluated": self.total_candidates_evaluated,
            "claims_approved": self.claims_approved,
            "claims_queued_for_review": self.claims_queued_for_review,
            "claims_rejected": self.claims_rejected,
            "average_trust_score": self.average_trust_score,
            "persisted_claim_ids": [str(cid) for cid in self.persisted_claim_ids],
            "executed_at": self.executed_at.isoformat(),
            "evaluations": [e.to_dict() for e in self.evaluations],
        }
