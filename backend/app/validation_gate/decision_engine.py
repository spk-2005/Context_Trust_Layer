"""
Layer 6: Claim Lifecycle Decision Engine.
Synthesizes 6-dimensional validation results into an authoritative lifecycle decision:
- [APPROVE] Automated activation for trusted, authoritative, and fully grounded claims.
- [REVIEW]  Human-in-the-Loop escalation for ambiguous, partial, or non-authoritative items.
- [REJECT]  Hard rejection for ungrounded claims or unauthorized scope violations.
"""

from __future__ import annotations

import logging
from app.extraction.models import CandidateClaim
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.validation_gate.evaluators import (
    AuthorityEvaluator,
    CompletenessEvaluator,
    MeaningEvaluator,
    ScopeEvaluator,
    SourceMatchEvaluator,
    TemporalValidityEvaluator,
)
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    DimensionEvaluation,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class ClaimLifecycleDecisionEngine:
    """Evaluates candidate claims across 6 dimensions and determines lifecycle actions."""

    # Dimension weightings for composite trust score
    WEIGHTS = {
        "source_match": 0.30,
        "meaning": 0.25,
        "authority": 0.20,
        "completeness": 0.15,
        "time": 0.10,
    }

    @classmethod
    def evaluate_candidate(
        cls,
        candidate: CandidateClaim,
        envelope: CanonicalSourceEnvelope,
    ) -> CandidateGateEvaluation:
        # 1. Evaluate 6 Core Dimensions
        source_match = SourceMatchEvaluator.evaluate(candidate, envelope)
        completeness = CompletenessEvaluator.evaluate(candidate)
        meaning = MeaningEvaluator.evaluate(candidate)
        scope = ScopeEvaluator.evaluate(candidate, envelope)
        time_eval = TemporalValidityEvaluator.evaluate(candidate, envelope)
        authority = AuthorityEvaluator.evaluate(envelope)

        # 2. Determine Human Review Trigger
        needs_review = (
            not meaning.passed
            or not completeness.passed
            or not authority.passed
            or not time_eval.passed
        )

        review_trigger = DimensionEvaluation(
            dimension_name="review",
            status=ReviewStatus.REVIEW_REQUIRED.value if needs_review else ReviewStatus.NO_REVIEW_NEEDED.value,
            score=0.5 if needs_review else 1.0,
            passed=not needs_review,
            reason="Human review recommended due to uncertainty or partial evidence." if needs_review else "All dimensions verified automatically without human review required.",
            details={"needs_human_review": needs_review},
        )

        # 3. Calculate Composite Trust Score
        composite_score = (
            source_match.score * cls.WEIGHTS["source_match"]
            + meaning.score * cls.WEIGHTS["meaning"]
            + authority.score * cls.WEIGHTS["authority"]
            + completeness.score * cls.WEIGHTS["completeness"]
            + time_eval.score * cls.WEIGHTS["time"]
        )
        composite_score = round(min(max(composite_score, 0.0), 1.0), 4)

        # 4. Synthesize Claim Lifecycle Decision
        claim_type = getattr(candidate, "claim_type", "policy")
        if claim_type == "descriptive_purpose":
            decision = ClaimLifecycleDecision.REJECT
            reason = "REJECTED: Descriptive purpose/preamble statement; non-normative context cannot be enforced as an operative constraint."
        elif claim_type == "derived_summary":
            decision = ClaimLifecycleDecision.REVIEW
            reason = "DERIVED SUMMARY: Retained for overview display; excluded from active decision gate to prevent duplicate evaluation against atomic row claims."
        # Fatal rules -> Hard REJECT
        elif not source_match.passed:
            decision = ClaimLifecycleDecision.REJECT
            reason = f"REJECTED: Grounding failure. {source_match.reason}"
        elif not scope.passed:
            decision = ClaimLifecycleDecision.REJECT
            reason = f"REJECTED: Scope violation. {scope.reason}"
        elif not meaning.passed and ("Subject-Evidence mismatch" in meaning.reason or meaning.status == "unsupported"):
            decision = ClaimLifecycleDecision.REJECT
            reason = f"REJECTED: Semantic grounding failure. {meaning.reason}"
        # HITL rules -> REVIEW
        elif needs_review or composite_score < 0.88:
            decision = ClaimLifecycleDecision.REVIEW
            reasons = []
            if not meaning.passed: reasons.append(meaning.reason)
            if not completeness.passed: reasons.append(completeness.reason)
            if not authority.passed: reasons.append(authority.reason)
            if not time_eval.passed: reasons.append(time_eval.reason)
            if composite_score < 0.88: reasons.append(f"Trust score {composite_score:.2f} is below 0.88 auto-approval threshold")
            reason = f"REVIEW: Human review recommended. {'; '.join(reasons)}"
        # All passed -> APPROVE
        else:
            decision = ClaimLifecycleDecision.APPROVE
            reason = f"APPROVED: All 6 dimensions verified. Trust score: {composite_score * 100:.1f}%."

        return CandidateGateEvaluation(
            candidate_id=candidate.candidate_id,
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            claim_text=candidate.claim_text,
            subject=candidate.subject,
            predicate=candidate.predicate,
            object_=candidate.object,
            evidence_text_span=candidate.evidence_text_span,
            claim_type=claim_type,
            modality=getattr(candidate, "modality", "POLICY_FACT"),
            conditions=getattr(candidate, "conditions", []),
            value=getattr(candidate, "value", None),
            unit=getattr(candidate, "unit", None),
            scope=getattr(candidate, "scope", {}),
            locator=getattr(candidate, "locator", {}),
            is_ambiguous=getattr(candidate, "is_ambiguous", False),
            ambiguity_reason=getattr(candidate, "ambiguity_reason", None),
            source_match=source_match,
            completeness=completeness,
            meaning=meaning,
            scope_eval=scope,
            time=time_eval,
            authority=authority,
            review_trigger=review_trigger,
            composite_trust_score=composite_score,
            lifecycle_decision=decision,
            decision_reason=reason,
        )
