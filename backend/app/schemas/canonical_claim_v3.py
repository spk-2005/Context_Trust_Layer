"""
Sprint AF-8: Revised Unified Claim Schema (v3.0)

Implements the formal enterprise claim data model with:
- Resolved counterparty & relationship tracking
- Typed conditions (TRIGGER, EXCEPTION, TIME_LIMIT, THRESHOLD, JURISDICTION)
- Independent evidence locator & verification status
- Hard certification gates (9 boolean knockout checks)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    CONTRACT = "CONTRACT"
    POLICY = "POLICY"
    HANDBOOK = "HANDBOOK"
    INVOICE = "INVOICE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    SOC_REPORT = "SOC_REPORT"


class ClaimType(str, Enum):
    RULE = "RULE"
    DEFINITION = "DEFINITION"
    DESCRIPTION = "DESCRIPTION"
    REFERENCE = "REFERENCE"
    EXAMPLE = "EXAMPLE"
    BILLING_TERM = "BILLING_TERM"
    LINE_ITEM = "LINE_ITEM"
    CONTROL_STATEMENT = "CONTROL_STATEMENT"


class ClaimStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    CANONICAL = "CANONICAL"
    REVIEW = "REVIEW"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class ModalityV3(str, Enum):
    MUST = "MUST"
    MUST_NOT = "MUST_NOT"
    MAY = "MAY"
    ENTITLED_TO = "ENTITLED_TO"
    ELIGIBLE_IF = "ELIGIBLE_IF"
    DEFINES = "DEFINES"
    DESCRIBES = "DESCRIBES"


class ActionTaxonomy(str, Enum):
    PAY = "PAY"
    PROVIDE = "PROVIDE"
    TERMINATE = "TERMINATE"
    LICENSE = "LICENSE"
    NOTIFY = "NOTIFY"
    INDEMNIFY = "INDEMNIFY"
    WARRANT = "WARRANT"
    AUDIT = "AUDIT"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    RESTRICTION = "RESTRICTION"
    GOVERNANCE = "GOVERNANCE"


class ConditionType(str, Enum):
    TRIGGER = "TRIGGER"
    EXCEPTION = "EXCEPTION"
    TIME_LIMIT = "TIME_LIMIT"
    THRESHOLD = "THRESHOLD"
    JURISDICTION = "JURISDICTION"


class SubjectPayload(BaseModel):
    raw_text: str
    canonical_entity: str
    entity_type: str = "PARTY"  # PARTY, ROLE, ENTITY
    confidence: float = 1.0


class CounterpartyPayload(BaseModel):
    raw_text: Optional[str] = None
    canonical_entity: Optional[str] = None
    relationship: Optional[str] = None  # OBLIGEE, BENEFICIARY, AFFECTED_PARTY, None


class PredicatePayload(BaseModel):
    raw_text: str
    action_taxonomy: str = ActionTaxonomy.GOVERNANCE.value
    normalized_action: str
    confidence: float = 1.0


class ObjectPayload(BaseModel):
    raw_text: str
    normalized_object: str


class ConditionV3(BaseModel):
    text: str
    type: ConditionType = ConditionType.TRIGGER


class EvidenceV3(BaseModel):
    verbatim_quote: str
    page: Optional[int] = 1
    char_start: int = -1
    char_end: int = -1
    bbox: List[float] = Field(default_factory=list)
    clause_text: str = ""
    entailment_score: float = 1.0
    verification_status: str = "EVIDENCE_VERIFIED"  # EVIDENCE_VERIFIED, EVIDENCE_PARTIAL, EVIDENCE_FAILED


class ProvenanceV3(BaseModel):
    extraction_version: str = "v13"
    normalizer_version: str = "v2.1"
    verifier_version: str = "v3.0-alpha"
    parent_claim_id: Optional[str] = None


class GatesV3(BaseModel):
    """The 9 Hard Certification Gates: all must be True for CANONICAL status."""
    span_exists: bool = False
    clause_entails_claim: bool = False
    subject_valid: bool = False
    counterparty_resolved: bool = True
    predicate_valid: bool = False
    is_atomic: bool = True
    is_not_duplicate: bool = True
    claim_type_allowed: bool = True
    human_approved_if_required: bool = True

    def is_all_passed(self) -> bool:
        return (
            self.span_exists
            and self.clause_entails_claim
            and self.subject_valid
            and self.counterparty_resolved
            and self.predicate_valid
            and self.is_atomic
            and self.is_not_duplicate
            and self.claim_type_allowed
            and self.human_approved_if_required
        )


class CanonicalClaimV3(BaseModel):
    """Enterprise Canonical Claim Model adhering to the v3.0 certified specification."""
    claim_id: str
    document_id: str
    clause_id: str
    source_type: SourceType = SourceType.CONTRACT
    claim_type: ClaimType = ClaimType.RULE
    status: ClaimStatus = ClaimStatus.CANDIDATE
    subject: SubjectPayload
    counterparty: Optional[CounterpartyPayload] = None
    predicate: PredicatePayload
    object: ObjectPayload
    modality: ModalityV3 = ModalityV3.MUST
    conditions: List[ConditionV3] = Field(default_factory=list)
    evidence: EvidenceV3
    provenance: ProvenanceV3 = Field(default_factory=ProvenanceV3)
    gates: GatesV3 = Field(default_factory=GatesV3)

    def evaluate_canonical_status(self) -> ClaimStatus:
        """Determines status strictly via hard boolean gates."""
        if self.gates.is_all_passed():
            self.status = ClaimStatus.CANONICAL
        elif not self.gates.is_not_duplicate:
            self.status = ClaimStatus.DUPLICATE
        elif not self.gates.span_exists or not self.gates.subject_valid or not self.gates.predicate_valid:
            self.status = ClaimStatus.REJECTED
        else:
            self.status = ClaimStatus.REVIEW
        return self.status
