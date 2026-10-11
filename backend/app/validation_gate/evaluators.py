"""
Layer 6: Multi-Dimensional Validation Gate Evaluators.
Evaluates candidate claims across the 6 core architecture dimensions:
1. Source Match (Pass / Fail)
2. Completeness (Complete / Partial)
3. Meaning (Supported / Uncertain)
4. Scope (In / Out)
5. Time (Current / Stale)
6. Authority (Authoritative / Non-Authoritative)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Tuple

from app.db.enums import SourceFamily, SourceIntent
from app.extraction.models import CandidateClaim
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.validation_gate.models import (
    AuthorityStatus,
    CompletenessStatus,
    DimensionEvaluation,
    MeaningStatus,
    ReviewStatus,
    ScopeStatus,
    SourceMatchStatus,
    TimeStatus,
)


class SourceMatchEvaluator:
    """Verifies cryptographic grounding proof and plugin validation from Layer 5."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        # Check Layer 5 verification outcome
        is_verified = candidate.status == "verified"
        has_plugin = bool(candidate.verification_plugin)
        has_details = bool(candidate.verification_details)

        if is_verified and has_plugin:
            return DimensionEvaluation(
                dimension_name="source_match",
                status=SourceMatchStatus.PASS.value,
                score=1.0,
                passed=True,
                reason=f"Cryptographically verified by Layer 5 plugin `{candidate.verification_plugin}`.",
                details={"plugin": candidate.verification_plugin, **candidate.verification_details},
            )
        else:
            return DimensionEvaluation(
                dimension_name="source_match",
                status=SourceMatchStatus.FAIL.value,
                score=0.0,
                passed=False,
                reason=f"Candidate was not verified by an evidence plugin (status: `{candidate.status}`).",
                details={"status": candidate.status},
            )


class CompletenessEvaluator:
    """Evaluates syntactic and attribute completeness of the extracted claim."""

    @staticmethod
    def evaluate(candidate: CandidateClaim) -> DimensionEvaluation:
        subj = (candidate.subject or "").strip()
        pred = (candidate.predicate or "").strip()
        obj = (candidate.object or "").strip()
        span = (candidate.evidence_text_span or "").strip()

        has_spo = bool(subj and pred and obj)
        has_evidence = bool(span)

        if has_spo and has_evidence:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.COMPLETE.value,
                score=1.0,
                passed=True,
                reason="Subject-Predicate-Object semantics and evidence coordinates are 100% complete.",
                details={"subject": subj, "predicate": pred, "object": obj},
            )
        else:
            missing = []
            if not subj: missing.append("subject")
            if not pred: missing.append("predicate")
            if not obj: missing.append("object")
            if not has_evidence: missing.append("evidence_span")

            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.6,
                passed=False,
                reason=f"Incomplete claim structure. Missing elements: {', '.join(missing)}.",
                details={"missing_fields": missing},
            )


class MeaningEvaluator:
    """Evaluates semantic clarity, confidence, and absence of speculative hedges."""

    # Words signaling uncertainty or hedges
    UNCERTAIN_HEDGES = re.compile(r"\b(might|maybe|possibly|perhaps|unclear|tentative|assumed|unconfirmed)\b", re.IGNORECASE)

    @classmethod
    def evaluate(cls, candidate: CandidateClaim) -> DimensionEvaluation:
        text = candidate.claim_text or ""
        confidence = candidate.confidence

        has_hedge = bool(cls.UNCERTAIN_HEDGES.search(text))

        if not has_hedge and confidence >= 0.80:
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.SUPPORTED.value,
                score=round(confidence, 4),
                passed=True,
                reason="Clear normative assertion with strong grounding confidence.",
                details={"confidence": confidence},
            )
        else:
            reason = "Speculative language or uncertainty detected." if has_hedge else f"Low semantic confidence ({confidence*100:.0f}%)."
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.UNCERTAIN.value,
                score=round(max(confidence * 0.5, 0.4), 4),
                passed=False,
                reason=reason,
                details={"confidence": confidence, "has_hedge": has_hedge},
            )


class ScopeEvaluator:
    """Enforces organizational tenant isolation and declared asset scope."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        org_id = str(envelope.organization_id)
        asset_id = envelope.asset_id
        
        # Check that candidate references the parent envelope
        envelope_match = candidate.envelope_id == envelope.envelope_id
        asset_match = candidate.asset_id == asset_id

        if envelope_match and asset_match:
            return DimensionEvaluation(
                dimension_name="scope",
                status=ScopeStatus.IN_SCOPE.value,
                score=1.0,
                passed=True,
                reason=f"Claim is within authorized tenant boundary `{org_id}` and asset scope.",
                details={"organization_id": org_id, "asset_id": asset_id},
            )
        else:
            return DimensionEvaluation(
                dimension_name="scope",
                status=ScopeStatus.OUT_OF_SCOPE.value,
                score=0.0,
                passed=False,
                reason="Asset ID or Envelope ID mismatch against authorized ingestion scope.",
                details={"expected_asset": asset_id, "claim_asset": candidate.asset_id},
            )


class TemporalValidityEvaluator:
    """Evaluates claim freshness, obsolescence, and expiration timeframes."""

    @staticmethod
    def evaluate(candidate: CandidateClaim, envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        captured_at = envelope.captured_at
        now = datetime.now(timezone.utc)
        
        # Calculate age in days
        age_days = (now - captured_at).total_seconds() / 86400.0

        # Fresh within 180 days (standard enterprise policy audit cycle)
        if age_days <= 180.0:
            freshness_score = max(round(1.0 - (age_days / 365.0) * 0.2, 4), 0.8)
            return DimensionEvaluation(
                dimension_name="time",
                status=TimeStatus.CURRENT.value,
                score=freshness_score,
                passed=True,
                reason=f"Source snapshot is current (captured {age_days:.1f} days ago).",
                details={"age_days": round(age_days, 1)},
            )
        else:
            return DimensionEvaluation(
                dimension_name="time",
                status=TimeStatus.STALE.value,
                score=0.4,
                passed=False,
                reason=f"Source snapshot exceeds 180-day freshness window ({age_days:.1f} days old).",
                details={"age_days": round(age_days, 1)},
            )


class AuthorityEvaluator:
    """Evaluates source hierarchy authority tier according to declared SourceIntent and SourceFamily."""

    @staticmethod
    def evaluate(envelope: CanonicalSourceEnvelope) -> DimensionEvaluation:
        intent = envelope.source_intent
        family = envelope.source_family

        # Tier 1: Canonical policies, DDL schemas, BSON database invariants (Authoritative)
        if intent in (SourceIntent.GOVERNANCE_POLICY, SourceIntent.OPERATIONAL_DATA) or family == SourceFamily.STRUCTURED:
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.AUTHORITATIVE.value,
                score=1.0,
                passed=True,
                reason=f"Primary authoritative enterprise source ({intent.value} / {family.value}).",
                details={"intent": intent.value, "family": family.value, "tier": 1},
            )

        # Tier 2: Factual knowledge, API catalogs, analytics metrics
        elif intent in (SourceIntent.FACTUAL_KNOWLEDGE, SourceIntent.ANALYTICS_METRIC):
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.AUTHORITATIVE.value,
                score=0.85,
                passed=True,
                reason=f"Secondary authoritative factual catalog ({intent.value}).",
                details={"intent": intent.value, "tier": 2},
            )

        # Tier 3: Discussions, comments, informal chat
        else:
            return DimensionEvaluation(
                dimension_name="authority",
                status=AuthorityStatus.NON_AUTHORITATIVE.value,
                score=0.50,
                passed=False,
                reason=f"Informational / non-authoritative discussion ({intent.value}).",
                details={"intent": intent.value, "tier": 3},
            )
