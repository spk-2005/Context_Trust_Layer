"""
Layer 6: Validation Gate & Persistence Pipeline.
Orchestrates candidate gate evaluation across 6 dimensions, determines lifecycle actions,
and coordinates persistence into the Enterprise Claim Store.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.models import CandidateClaim, Layer5ExtractionResult
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    Layer6ValidationResult,
)
from app.validation_gate.persistence import EnterpriseClaimStore

logger = logging.getLogger(__name__)


class Layer6ValidationGatePipeline:
    """End-to-end pipeline orchestrator for Layer 6: Validation Gate & Persistence."""

    def __init__(self, persist_to_db: bool = True):
        self.persist_to_db = persist_to_db

    async def process_extraction_result(
        self,
        envelope: CanonicalSourceEnvelope,
        extraction_result: Layer5ExtractionResult,
        session: Optional[AsyncSession] = None,
    ) -> Layer6ValidationResult:
        """
        Takes candidate claims from Layer 5, evaluates them through the 6-dimensional
        Validation Gate, determines lifecycle actions, and persists them into the Enterprise Claim Store.
        """
        evaluations: List[CandidateGateEvaluation] = []
        candidates_map: dict[str, CandidateClaim] = {}

        approved_count = 0
        review_count = 0
        rejected_count = 0
        trust_scores_sum = 0.0

        for candidate in extraction_result.candidates:
            candidates_map[candidate.candidate_id] = candidate

            # Run 6-Dimensional Validation Gate & Decision Engine
            gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(
                candidate=candidate,
                envelope=envelope,
            )
            evaluations.append(gate_eval)
            trust_scores_sum += gate_eval.composite_trust_score

            if gate_eval.lifecycle_decision == ClaimLifecycleDecision.APPROVE:
                approved_count += 1
            elif gate_eval.lifecycle_decision == ClaimLifecycleDecision.REVIEW:
                review_count += 1
            else:
                rejected_count += 1

        total_evaluated = len(evaluations)
        avg_trust_score = round(trust_scores_sum / max(total_evaluated, 1), 4)

        persisted_ids = []
        if self.persist_to_db and evaluations:
            try:
                persisted_ids = await EnterpriseClaimStore.persist_evaluations(
                    evaluations=evaluations,
                    candidates_map=candidates_map,
                    envelope=envelope,
                    session=session,
                )
            except Exception as e:
                logger.error("Failed to persist evaluated claims to Enterprise Claim Store: %s", str(e), exc_info=True)

        return Layer6ValidationResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            total_candidates_evaluated=total_evaluated,
            claims_approved=approved_count,
            claims_queued_for_review=review_count,
            claims_rejected=rejected_count,
            average_trust_score=avg_trust_score,
            evaluations=evaluations,
            persisted_claim_ids=persisted_ids,
        )


# Global singleton instance
global_validation_gate = Layer6ValidationGatePipeline(persist_to_db=True)
