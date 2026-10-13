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
    """Evaluates syntactic, attribute, and condition completeness of the extracted claim."""

    @staticmethod
    def evaluate(candidate: CandidateClaim) -> DimensionEvaluation:
        subj = (candidate.subject or "").strip()
        pred = (candidate.predicate or "").strip()
        obj = (candidate.object or "").strip()
        span = (candidate.evidence_text_span or "").strip()
        is_ambiguous = getattr(candidate, "is_ambiguous", False)
        ambiguity_reason = getattr(candidate, "ambiguity_reason", None)

        has_spo = bool(subj and pred and obj)
        has_evidence = bool(span)

        if is_ambiguous:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.7,
                passed=False,
                reason=f"Ambiguous structure or cell mapping: {ambiguity_reason or 'Mapping requires review'}.",
                details={"subject": subj, "predicate": pred, "object": obj, "is_ambiguous": True},
            )

        PRONOUN_SUBJECTS = {"it", "they", "this", "that", "these", "those", "which", "he", "she", "there", "someone"}
        if subj.lower() in PRONOUN_SUBJECTS:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.2,
                passed=False,
                reason=f"Fragment detected: Subject is an ungrounded pronoun ('{subj}'). Complete assertion with named entity required.",
                details={"subject": subj, "predicate": pred, "object": obj, "is_fragment": True},
            )

        if not (has_spo and has_evidence):
            missing = []
            if not subj: missing.append("subject")
            if not pred: missing.append("predicate")
            if not obj: missing.append("object")
            if not has_evidence: missing.append("evidence_text_span")

            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.6,
                passed=False,
                reason=f"Fragment detected: Claim is missing mandatory attributes: {', '.join(missing)}.",
                details={"missing_attributes": missing, "is_fragment": True},
            )

        if pred.lower() in ("is", "has", "are", "have", "the", "a", "an"):
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.3,
                passed=False,
                reason=f"Fragment detected: Predicate '{pred}' lacks normative relation or semantic action.",
                details={"predicate": pred, "is_fragment": True},
            )

        details_dict: dict[str, Any] = {"subject": subj, "predicate": pred, "object": obj}
        if getattr(candidate, "conditions", None):
            details_dict["conditions"] = candidate.conditions
        if getattr(candidate, "value", None) is not None:
            details_dict["value"] = candidate.value
            details_dict["unit"] = getattr(candidate, "unit", None)
        if getattr(candidate, "scope", None):
            details_dict["scope"] = candidate.scope

        # Grounding check for contextual preconditions / exceptions
        unsupported_conditions = []
        if getattr(candidate, "conditions", None):
            import json
            ev_corpus = (
                span + " " +
                str(getattr(candidate, "claim_text", "") or "") + " " +
                json.dumps(getattr(candidate, "structured_values", {}) or {}, default=str) + " " +
                json.dumps(getattr(candidate, "locator", {}) or {}, default=str)
            ).lower()
            stop_tokens = {
                "and", "the", "for", "with", "all", "status", "criteria", "per",
                "upon", "under", "from", "any", "not", "require", "requires", "must", "shall", "or",
                "employee", "employees", "employment", "staff", "role", "state", "applicable", "policy"
            }
            for cond in candidate.conditions:
                cond_words = [
                    w.lower() for w in re.findall(r"[a-zA-Z]{3,}", str(cond))
                    if w.lower() not in stop_tokens
                ]
                missing_words = [
                    w for w in cond_words
                    if w not in ev_corpus and (len(w) < 5 or w[:5] not in ev_corpus)
                ]
                if missing_words:
                    unsupported_conditions.append(f"Condition '{cond}' has ungrounded terms: {', '.join(missing_words)}")

        if unsupported_conditions:
            return DimensionEvaluation(
                dimension_name="completeness",
                status=CompletenessStatus.PARTIAL.value,
                score=0.65,
                passed=False,
                reason=f"Unsupported conditions detected: {'; '.join(unsupported_conditions)}.",
                details={"unsupported_conditions": unsupported_conditions, **details_dict},
            )

        return DimensionEvaluation(
            dimension_name="completeness",
            status=CompletenessStatus.COMPLETE.value,
            score=1.0,
            passed=True,
            reason="Subject-Predicate-Object semantics, conditions, and evidence coordinates are 100% complete.",
            details=details_dict,
        )


class MeaningEvaluator:
    """Evaluates semantic clarity, deontic consistency, confidence, and absence of speculative hedges."""

    # Words signaling uncertainty or hedges
    UNCERTAIN_HEDGES = re.compile(r"\b(might|maybe|possibly|perhaps|unclear|tentative|assumed|unconfirmed)\b", re.IGNORECASE)
    OBLIGATION_EVIDENCE = re.compile(r"\b(must|shall|required|requires|mandates?|mandatory|obligated|has to|have to|return)\b", re.IGNORECASE)
    PROHIBITION_EVIDENCE = re.compile(r"\b(prohibited|shall not|must not|forbidden|strictly prohibited|unauthorized\s+.*?\s+prohibited)\b", re.IGNORECASE)

    @classmethod
    def evaluate(cls, candidate: CandidateClaim) -> DimensionEvaluation:
        text = candidate.claim_text or ""
        evidence = candidate.evidence_text_span or ""
        confidence = candidate.confidence
        modality = getattr(candidate, "modality", "POLICY_FACT")

        has_hedge = bool(cls.UNCERTAIN_HEDGES.search(text))

        # 1. Subject-Evidence Grounding Validation
        # The asserted subject must be semantically grounded in the claim's own evidence span
        subj_words = [
            w.lower()
            for w in re.findall(r"[a-zA-Z]{3,}", candidate.subject or "")
            if w.lower() not in {"the", "and", "for", "with", "all", "per", "from", "any", "upon", "under", "into"}
        ]
        ev_lower = evidence.lower()
        has_table_grid = bool(getattr(candidate, "locator", {}) and candidate.locator.get("table_grid"))
        is_derived_summary = bool(getattr(candidate, "claim_type", "") == "derived_summary")
        from app.extraction.models import ExtractionStrategyType
        is_structured_schema = bool(getattr(candidate, "extraction_strategy", None) == ExtractionStrategyType.DETERMINISTIC_SCHEMA)

        if subj_words and not has_table_grid and not is_derived_summary and not is_structured_schema:
            matched_subj = any(w in ev_lower for w in subj_words)
            # Allow general policy/governance meta subjects if evidence mentions policy/guideline
            is_doc_meta_subj = any(w in {"policy", "governance", "document"} for w in subj_words) and ("policy" in ev_lower or "guideline" in ev_lower)
            if not matched_subj and not is_doc_meta_subj:
                return DimensionEvaluation(
                    dimension_name="meaning",
                    status=MeaningStatus.UNSUPPORTED.value,
                    score=0.20,
                    passed=False,
                    reason=f"Subject-Evidence mismatch: asserted subject '{candidate.subject}' has no grounding in the underlying evidence span.",
                    details={"subject": candidate.subject, "evidence": evidence[:120], "subject_unsupported": True},
                )

        # 2. Deontic consistency verification against evidence text
        deontic_mismatch = False
        discretionary_phrases = ("holds the right", "holds right", "may request", "may", "permitted", "option to", "at its discretion")
        has_discretionary = any(p in evidence.lower() or p in text.lower() for p in discretionary_phrases)

        if modality == "OBLIGATION" and (has_discretionary or not cls.OBLIGATION_EVIDENCE.search(evidence)):
            deontic_mismatch = True
        elif modality == "PROHIBITION" and not cls.PROHIBITION_EVIDENCE.search(evidence):
            deontic_mismatch = True

        if deontic_mismatch:
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.UNCERTAIN.value,
                score=0.20,
                passed=False,
                reason=f"Deontic mismatch: claim claims {modality} but underlying source evidence reflects discretionary/permissive phrasing or lacks normative imperative verbs.",
                details={"confidence": confidence, "modality": modality, "deontic_mismatch": True},
            )

        if not has_hedge and confidence >= 0.88:
            return DimensionEvaluation(
                dimension_name="meaning",
                status=MeaningStatus.SUPPORTED.value,
                score=round(confidence, 4),
                passed=True,
                reason="Clear assertion with verified deontic alignment and strong grounding confidence.",
                details={"confidence": confidence, "modality": modality},
            )
        else:
            reason = "Speculative language or uncertainty detected." if has_hedge else f"Sub-threshold semantic confidence ({confidence*100:.0f}% < 88%)."
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
