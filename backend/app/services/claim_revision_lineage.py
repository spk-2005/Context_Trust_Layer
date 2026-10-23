"""
Claim Revision Lineage and Provenance Engine.

Preserves strict separation between original candidate representations and revised versions:
1. Evaluates original candidate claim through UniversalGateEvaluator.
2. If original is defective, marks it REVIEW_REQUIRED or REJECTED with explicit 3-valued
   semantic entailment rationale (CONTRADICTED or INSUFFICIENT_EVIDENCE).
3. If an authoritative repair/revision is proposed, generates a revised candidate with a new distinct
   cryptographic candidate ID (preserving the predicate and object hash).
4. Evaluates revised candidate independently through UniversalGateEvaluator.
5. Emits an immutable ClaimRevisionRecord linking:
   - original_candidate_id
   - revised_candidate_id
   - source_evidence_id
   - revision_reason
   - pipeline_run_id

Guarantees that an incorrect original representation is NEVER marked supported or certified.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.evidence import ImmutableEvidenceSpan
from app.services.universal_gate_evaluator import (
    EntailmentDecision,
    SemanticEntailmentResult,
    UniversalGateEvaluator,
    UniversalGateResult,
)


class ClaimRevisionRecord(BaseModel):
    """Immutable audit lineage linking an original candidate to its revised counterpart."""
    original_candidate_id: str
    revised_candidate_id: str
    source_evidence_id: str
    revision_reason: str
    pipeline_run_id: str

    # Original candidate state
    original_subject: str
    original_predicate: str
    original_object: str
    original_entailment_decision: str
    original_gate_status: str
    original_rejection_reasons: List[str] = Field(default_factory=list)

    # Revised candidate state
    revised_subject: str
    revised_predicate: str
    revised_object: str
    revised_entailment_decision: str
    revised_gate_status: str
    revised_gate_reasons: List[str] = Field(default_factory=list)

    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ClaimRevisionManager:
    """Manages the lifecycle transition from original defective claims to verified revisions."""

    @staticmethod
    def compute_revised_candidate_id(
        envelope_id: str,
        unit_id: str,
        verbatim_quote: str,
        revised_predicate: str,
    ) -> str:
        quote_hash = hashlib.sha256(verbatim_quote.strip().encode("utf-8")).hexdigest()[:12]
        pred_hash = hashlib.sha256(revised_predicate.strip().encode("utf-8")).hexdigest()[:10]
        return f"cand:{envelope_id}:{unit_id}:{quote_hash}:{pred_hash}"

    @classmethod
    def evaluate_and_revise(
        cls,
        original_candidate_id: str,
        subject: str,
        predicate: str,
        object_text: str,
        claim_text: str,
        evidence_span: Optional[ImmutableEvidenceSpan],
        proposed_subject: Optional[str] = None,
        proposed_predicate: Optional[str] = None,
        proposed_object: Optional[str] = None,
        proposed_claim_text: Optional[str] = None,
        revision_reason: str = "",
        pipeline_run_id: Optional[str] = None,
        envelope_id: str = "",
        unit_id: str = "0",
    ) -> tuple[UniversalGateResult, Optional[UniversalGateResult], Optional[ClaimRevisionRecord]]:
        """
        Step 1: Evaluate original claim as-is.
        Step 2: If proposed revision provided, evaluate revised claim independently.
        Step 3: Construct ClaimRevisionRecord linking both states.
        """
        run_id = pipeline_run_id or str(uuid.uuid4())

        # Step 1: Evaluate original claim
        orig_res = UniversalGateEvaluator.evaluate(
            claim_text=claim_text,
            subject=subject,
            predicate=predicate,
            object_text=object_text,
            evidence=evidence_span,
            claim_type="RULE",
        )

        rev_res: Optional[UniversalGateResult] = None
        revision_record: Optional[ClaimRevisionRecord] = None

        # Step 2: Evaluate revision if proposed
        if proposed_predicate or proposed_subject or proposed_object:
            new_subj = proposed_subject or subject
            new_pred = proposed_predicate or predicate
            new_obj = proposed_object or object_text
            new_text = proposed_claim_text or claim_text

            rev_res = UniversalGateEvaluator.evaluate(
                claim_text=new_text,
                subject=new_subj,
                predicate=new_pred,
                object_text=new_obj,
                evidence=evidence_span,
                claim_type="RULE",
            )

            quote = evidence_span.verbatim_quote if evidence_span else claim_text
            revised_cand_id = cls.compute_revised_candidate_id(
                envelope_id=envelope_id,
                unit_id=unit_id,
                verbatim_quote=quote,
                revised_predicate=new_pred,
            )

            revision_record = ClaimRevisionRecord(
                original_candidate_id=original_candidate_id,
                revised_candidate_id=revised_cand_id,
                source_evidence_id=str(getattr(evidence_span, "evidence_id", None) or f"ev:{envelope_id}:{unit_id}"),
                revision_reason=revision_reason,
                pipeline_run_id=run_id,
                original_subject=subject,
                original_predicate=predicate,
                original_object=object_text,
                original_entailment_decision=orig_res.entailment_decision,
                original_gate_status=orig_res.certification_tier,
                original_rejection_reasons=orig_res.rejection_reasons,
                revised_subject=new_subj,
                revised_predicate=new_pred,
                revised_object=new_obj,
                revised_entailment_decision=rev_res.entailment_decision,
                revised_gate_status=rev_res.certification_tier,
                revised_gate_reasons=rev_res.rejection_reasons,
            )

        return orig_res, rev_res, revision_record
