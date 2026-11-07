import decimal
import math
from datetime import datetime, timezone
from typing import NamedTuple


class TrustScoreBreakdown(NamedTuple):
    source_score: decimal.Decimal
    freshness_score: decimal.Decimal
    evidence_score: decimal.Decimal
    consistency_score: decimal.Decimal
    authority_score: decimal.Decimal
    human_score: decimal.Decimal
    overall_score: decimal.Decimal


class TrustScoreCalculator:
    """Calculates multi-factor trust scores for extracted claims."""

    def __init__(
        self,
        weight_source: float = 0.30,
        weight_freshness: float = 0.25,
        weight_evidence: float = 0.20,
        weight_consistency: float = 0.15,
        weight_authority: float = 0.10,
        freshness_half_life_days: float = 365.0,
    ):
        self.w_source = weight_source
        self.w_freshness = weight_freshness
        self.w_evidence = weight_evidence
        self.w_consistency = weight_consistency
        self.w_authority = weight_authority
        self.half_life_days = freshness_half_life_days

    def calculate_freshness(self, doc_created_at: datetime | None) -> float:
        if not doc_created_at:
            return 0.90

        now = datetime.now(timezone.utc)
        if doc_created_at.tzinfo is None:
            doc_created_at = doc_created_at.replace(tzinfo=timezone.utc)

        age_days = max(0.0, (now - doc_created_at).total_seconds() / 86400.0)
        # Exponential decay: score = e^(-lambda * days)
        decay_lambda = math.log(2) / self.half_life_days
        freshness = math.exp(-decay_lambda * age_days)
        return max(0.0, min(1.0, freshness))

    def calculate(
        self,
        source_authority_level: int = 50,
        doc_created_at: datetime | None = None,
        has_evidence: bool = True,
        is_current_version: bool = True,
        has_conflicts: bool = False,
        conflict_confidence: float = 0.0,
        human_adjustment: float = 0.0,
        # Phase 7: Explicit Multi-Factor Signals
        extraction_status: str | None = None,
        extraction_quality_score: float | None = None,
        has_valid_locator: bool = True,
        evidence_relevance_score: float | None = None,
        claim_completeness_score: float | None = None,
        has_missing_conditions: bool = False,
        has_missing_exceptions: bool = False,
        validation_status: str | None = None,
    ) -> TrustScoreBreakdown:
        # 1. Source Authority Score (0.0 to 1.0, strictly from source hierarchy, NOT extraction confidence)
        source_val = max(0.0, min(1.0, source_authority_level / 100.0))

        # 2. Source Currentness & Freshness Score
        freshness_val = self.calculate_freshness(doc_created_at)
        if not is_current_version:
            freshness_val *= 0.50  # penalty for superseded versions

        # 3. Evidence Quality, Locator Validity & Relevance Score
        evidence_val = 0.95 if has_evidence else 0.40

        # Adjust for Layer 4 extraction status
        if extraction_status:
            ext_norm = extraction_status.lower().strip()
            if ext_norm in ("failed", "empty", "error"):
                evidence_val = 0.05
            elif ext_norm in ("needs_ocr", "ocr_required"):
                evidence_val = min(evidence_val, 0.35)
            elif ext_norm == "partial":
                evidence_val = min(evidence_val, 0.70)
            elif ext_norm in ("success", "extracted"):
                evidence_val = max(evidence_val, 0.90)

        if extraction_quality_score is not None:
            evidence_val = min(evidence_val, max(0.05, float(extraction_quality_score)))

        # Penalize missing or invalid locators
        if not has_valid_locator:
            evidence_val = min(evidence_val * 0.35, 0.30)

        # Evidence relevance adjustment
        if evidence_relevance_score is not None:
            evidence_val *= max(0.10, min(1.0, float(evidence_relevance_score)))

        # Layer 6 Validation Status impact on evidence score
        if validation_status:
            val_norm = validation_status.upper().strip()
            if val_norm == "INSUFFICIENT_EVIDENCE":
                evidence_val = min(evidence_val, 0.25)
            elif val_norm == "SUPPORTED":
                evidence_val = max(evidence_val, 0.95)

        # 4. Consistency & Contradiction Score
        consistency_val = 1.00
        if has_conflicts or (validation_status and validation_status.upper() == "CONTRADICTED"):
            conf_level = max(conflict_confidence, 0.95) if (validation_status and validation_status.upper() == "CONTRADICTED") else conflict_confidence
            consistency_val = max(0.05, 1.00 - (conf_level * 0.85))

        # 5. Authority Score
        authority_val = 0.90 if is_current_version else 0.50

        # 6. Human Score
        human_val = max(-1.0, min(1.0, human_adjustment))

        # 7. Weighted Composite Score
        overall = (
            (self.w_source * source_val)
            + (self.w_freshness * freshness_val)
            + (self.w_evidence * evidence_val)
            + (self.w_consistency * consistency_val)
            + (self.w_authority * authority_val)
            + human_val
        )
        overall = max(0.0, min(1.0, overall))

        # Phase 7 Fail-Closed Guardrails:
        # Rule 1: Do not award high trust to a claim with missing conditions or exceptions
        if has_missing_conditions or has_missing_exceptions or (claim_completeness_score is not None and claim_completeness_score < 0.80):
            overall = min(overall, 0.65)

        # Rule 2: Do not award high trust to a claim with failed extraction or invalid provenance
        if (extraction_status and extraction_status.lower() in ("failed", "empty", "error")) or not has_valid_locator:
            overall = min(overall, 0.30)

        # Rule 3: Contradicted claims must be strictly capped
        if validation_status and validation_status.upper() == "CONTRADICTED":
            overall = min(overall, 0.20)
        elif validation_status and validation_status.upper() == "INSUFFICIENT_EVIDENCE":
            overall = min(overall, 0.50)
        elif validation_status and validation_status.upper() == "NEEDS_REVIEW":
            overall = min(overall, 0.70)

        to_dec = lambda x: decimal.Decimal(f"{x:.4f}")

        return TrustScoreBreakdown(
            source_score=to_dec(source_val),
            freshness_score=to_dec(freshness_val),
            evidence_score=to_dec(evidence_val),
            consistency_score=to_dec(consistency_val),
            authority_score=to_dec(authority_val),
            human_score=to_dec(max(0.0, human_val)),
            overall_score=to_dec(overall),
        )
