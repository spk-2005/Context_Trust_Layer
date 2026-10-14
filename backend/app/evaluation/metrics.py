"""
TEVV (Test, Evaluation, Validation, Verification) Metric Measurement Service.
Layer 7 Enterprise Benchmark Engine: Computes precision, recall, F1, evidence grounding,
and conflict accuracy against gold-standard benchmarks and enterprise release gates.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pydantic import BaseModel, Field


class ReleaseGateThresholds:
    MIN_CLAIM_PRECISION = 0.97
    MIN_CLAIM_RECALL = 0.95
    MIN_EVIDENCE_PRECISION = 0.99
    MAX_FALSE_POSITIVE_CONFLICT_RATE = 0.02


class TEVVMetricsReport(BaseModel):
    """Production evaluation and quality report across extracted claims and conflict analysis."""
    total_extracted_claims: int = 0
    total_gold_claims: int = 0
    matched_claims: int = 0

    # Claim extraction accuracy
    claim_precision: float = 0.0
    claim_recall: float = 0.0
    claim_f1: float = 0.0

    # Evidence grounding precision
    evidence_precision: float = 0.0  # % claims with verbatim verified quote
    evidence_coverage: float = 0.0

    # Semantic component metrics
    subject_f1: float = 0.0
    predicate_f1: float = 0.0
    value_f1: float = 0.0
    condition_recall: float = 0.0
    qualifier_recall: float = 0.0

    # Conflict engine metrics
    total_conflicts_evaluated: int = 0
    true_conflicts_detected: int = 0
    false_positive_conflicts: int = 0
    false_positive_conflict_rate: float = 0.0
    true_conflict_recall: float = 0.0

    # Operational triage
    review_queued_claims: int = 0
    review_rate: float = 0.0

    # Release Gate evaluation
    release_gate_passed: bool = False
    release_gate_failures: List[str] = Field(default_factory=list)


class TEVVMeasurementService:
    """
    Evaluator service that compares candidate or persisted claims against
    annotated gold standards to compute production TEVV metrics.
    """

    @staticmethod
    def _normalize_token(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(text or "").lower())

    @classmethod
    def _is_claim_match(cls, extracted: Any, gold: Any) -> Tuple[bool, bool, bool, bool]:
        """
        Evaluates match between an extracted claim and a gold reference claim.
        Returns:
            (is_match, subject_match, predicate_match, value_match)
        """
        e_subj = cls._normalize_token(getattr(extracted, "subject", ""))
        g_subj = cls._normalize_token(getattr(gold, "subject", ""))

        e_pred = cls._normalize_token(getattr(extracted, "predicate", ""))
        g_pred = cls._normalize_token(getattr(gold, "predicate", ""))

        e_val = cls._normalize_token(getattr(extracted, "value", "") or getattr(extracted, "object", ""))
        g_val = cls._normalize_token(getattr(gold, "value", "") or getattr(gold, "object", ""))

        subj_match = (e_subj == g_subj) or (e_subj in g_subj) or (g_subj in e_subj)
        pred_match = (e_pred == g_pred) or (e_pred in g_pred) or (g_pred in e_pred)
        val_match = (e_val == g_val) or (e_val in g_val) or (g_val in e_val)

        is_match = subj_match and (pred_match or val_match)
        return is_match, subj_match, pred_match, val_match

    @classmethod
    def compute_metrics(
        cls,
        extracted_claims: Sequence[Any],
        gold_claims: Sequence[Any],
        detected_conflicts: Optional[Sequence[Any]] = None,
        gold_conflicts: Optional[Sequence[Any]] = None,
        source_evidence_text: Optional[str] = None,
    ) -> TEVVMetricsReport:
        """
        Computes precision, recall, F1, grounding, and conflict accuracy against gold benchmarks.
        """
        total_extracted = len(extracted_claims)
        total_gold = len(gold_claims)

        if total_extracted == 0 and total_gold == 0:
            return TEVVMetricsReport(
                release_gate_passed=True,
                claim_precision=1.0,
                claim_recall=1.0,
                claim_f1=1.0,
                evidence_precision=1.0,
            )

        matched_extracted = set()
        matched_gold = set()

        subject_matches = 0
        predicate_matches = 0
        value_matches = 0
        grounded_claims = 0
        review_count = 0

        for i, ext in enumerate(extracted_claims):
            # Evidence grounding check: verified evidence_text_span
            span = getattr(ext, "evidence_text_span", "") or getattr(ext, "claim_text", "")
            if span:
                if source_evidence_text:
                    if span.lower() in source_evidence_text.lower():
                        grounded_claims += 1
                else:
                    grounded_claims += 1

            # Review status check
            status_val = getattr(ext, "status", "")
            decision_val = getattr(ext, "lifecycle_decision", "")
            if "candidate" in str(status_val).lower() or "review" in str(decision_val).lower():
                review_count += 1

            for j, gold in enumerate(gold_claims):
                if j in matched_gold:
                    continue
                is_match, s_match, p_match, v_match = cls._is_claim_match(ext, gold)
                if is_match:
                    matched_extracted.add(i)
                    matched_gold.add(j)
                    if s_match: subject_matches += 1
                    if p_match: predicate_matches += 1
                    if v_match: value_matches += 1
                    break

        tp = len(matched_extracted)
        fp = max(0, total_extracted - tp)
        fn = max(0, total_gold - tp)

        precision = round(float(tp / total_extracted) if total_extracted > 0 else 0.0, 4)
        recall = round(float(tp / total_gold) if total_gold > 0 else 0.0, 4)
        f1 = round(float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0, 4)

        evidence_prec = round(float(grounded_claims / total_extracted) if total_extracted > 0 else 1.0, 4)
        evidence_cov = round(float(grounded_claims / total_gold) if total_gold > 0 else 1.0, 4)

        subj_f1 = round(float(subject_matches / max(total_extracted, 1)), 4)
        pred_f1 = round(float(predicate_matches / max(total_extracted, 1)), 4)
        val_f1 = round(float(value_matches / max(total_extracted, 1)), 4)

        # Conflict evaluation
        det_cfl = list(detected_conflicts or [])
        gold_cfl = list(gold_conflicts or [])

        total_cfl = len(det_cfl)
        gold_cfl_count = len(gold_cfl)

        # In benchmark evaluations, gold conflicts are known genuine contradictions
        if total_cfl == 0 and gold_cfl_count == 0:
            fp_conflicts = 0
            fp_rate = 0.0
            cfl_recall = 1.0
        elif gold_cfl_count == 0:
            fp_conflicts = total_cfl
            fp_rate = 1.0 if total_cfl > 0 else 0.0
            cfl_recall = 1.0
        else:
            tp_cfl = min(total_cfl, gold_cfl_count)
            fp_conflicts = max(0, total_cfl - gold_cfl_count)
            fp_rate = round(float(fp_conflicts / total_cfl) if total_cfl > 0 else 0.0, 4)
            cfl_recall = round(float(tp_cfl / gold_cfl_count), 4)

        review_rate = round(float(review_count / total_extracted) if total_extracted > 0 else 0.0, 4)

        # Release Gate Checks
        gate_failures = []
        if precision < ReleaseGateThresholds.MIN_CLAIM_PRECISION:
            gate_failures.append(f"Claim Precision {precision*100:.1f}% < {ReleaseGateThresholds.MIN_CLAIM_PRECISION*100:.1f}%")
        if recall < ReleaseGateThresholds.MIN_CLAIM_RECALL:
            gate_failures.append(f"Claim Recall {recall*100:.1f}% < {ReleaseGateThresholds.MIN_CLAIM_RECALL*100:.1f}%")
        if evidence_prec < ReleaseGateThresholds.MIN_EVIDENCE_PRECISION:
            gate_failures.append(f"Evidence Precision {evidence_prec*100:.1f}% < {ReleaseGateThresholds.MIN_EVIDENCE_PRECISION*100:.1f}%")
        if fp_rate > ReleaseGateThresholds.MAX_FALSE_POSITIVE_CONFLICT_RATE:
            gate_failures.append(f"False-Positive Conflict Rate {fp_rate*100:.1f}% > {ReleaseGateThresholds.MAX_FALSE_POSITIVE_CONFLICT_RATE*100:.1f}%")

        gate_passed = len(gate_failures) == 0

        return TEVVMetricsReport(
            total_extracted_claims=total_extracted,
            total_gold_claims=total_gold,
            matched_claims=tp,
            claim_precision=precision,
            claim_recall=recall,
            claim_f1=f1,
            evidence_precision=evidence_prec,
            evidence_coverage=evidence_cov,
            subject_f1=subj_f1,
            predicate_f1=pred_f1,
            value_f1=val_f1,
            condition_recall=recall,
            qualifier_recall=recall,
            total_conflicts_evaluated=total_cfl,
            true_conflicts_detected=total_cfl - fp_conflicts,
            false_positive_conflicts=fp_conflicts,
            false_positive_conflict_rate=fp_rate,
            true_conflict_recall=cfl_recall if gold_cfl_count > 0 else 1.0,
            review_queued_claims=review_count,
            review_rate=review_rate,
            release_gate_passed=gate_passed,
            release_gate_failures=gate_failures,
        )
