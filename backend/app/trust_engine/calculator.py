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
    ) -> TrustScoreBreakdown:
        # 1. Source Score (0.0 to 1.0)
        source_val = max(0.0, min(1.0, source_authority_level / 100.0))

        # 2. Freshness Score
        freshness_val = self.calculate_freshness(doc_created_at)
        if not is_current_version:
            freshness_val *= 0.50  # penalty for superseded versions

        # 3. Evidence Score
        evidence_val = 0.95 if has_evidence else 0.40

        # 4. Consistency Score
        consistency_val = 1.00
        if has_conflicts:
            consistency_val = max(0.10, 1.00 - (conflict_confidence * 0.70))

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
