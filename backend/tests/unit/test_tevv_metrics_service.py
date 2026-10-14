import pytest
from app.evaluation.metrics import TEVVMeasurementService, TEVVMetricsReport, ReleaseGateThresholds


class DummyClaim:
    def __init__(self, subject: str, predicate: str, value: str, evidence_span: str = "", status: str = "verified"):
        self.subject = subject
        self.predicate = predicate
        self.value = value
        self.object = value
        self.claim_text = f"{subject} {predicate} {value}"
        self.evidence_text_span = evidence_span or self.claim_text
        self.status = status


def test_tevv_metrics_perfect_match():
    """Verifies that identical extracted and gold claims yield 1.0 precision, recall, and pass release gate."""
    gold_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
        DummyClaim("Gold members", "has_return_window", "60 days"),
        DummyClaim("Holiday purchases", "has_return_deadline", "January 31"),
    ]
    extracted_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
        DummyClaim("Gold members", "has_return_window", "60 days"),
        DummyClaim("Holiday purchases", "has_return_deadline", "January 31"),
    ]

    report = TEVVMeasurementService.compute_metrics(extracted_claims, gold_claims)
    assert report.total_extracted_claims == 3
    assert report.total_gold_claims == 3
    assert report.claim_precision == 1.0
    assert report.claim_recall == 1.0
    assert report.claim_f1 == 1.0
    assert report.evidence_precision == 1.0
    assert report.false_positive_conflict_rate == 0.0
    assert report.release_gate_passed is True
    assert len(report.release_gate_failures) == 0


def test_tevv_metrics_precision_gate_failure():
    """Verifies that spurious/unmatched extracted claims trigger release gate failure."""
    gold_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
    ]
    extracted_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
        DummyClaim("Non-existent policy", "invalid_pred", "99 days"),
    ]

    report = TEVVMeasurementService.compute_metrics(extracted_claims, gold_claims)
    assert report.claim_precision == 0.5
    assert report.claim_recall == 1.0
    assert report.release_gate_passed is False
    assert any("Claim Precision" in f for f in report.release_gate_failures)


def test_tevv_metrics_conflict_false_positive_gate():
    """Verifies that false positive conflicts trigger gate failure when rate > 2%."""
    gold_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
    ]
    extracted_claims = [
        DummyClaim("Standard merchandise", "has_return_window", "30 days"),
    ]
    # 0 gold conflicts, but 2 detected false positive conflicts
    detected_conflicts = [{"claim_a": "1", "claim_b": "2"}, {"claim_a": "3", "claim_b": "4"}]
    gold_conflicts = []

    report = TEVVMeasurementService.compute_metrics(
        extracted_claims,
        gold_claims,
        detected_conflicts=detected_conflicts,
        gold_conflicts=gold_conflicts,
    )
    assert report.false_positive_conflict_rate == 1.0
    assert report.release_gate_passed is False
    assert any("False-Positive Conflict Rate" in f for f in report.release_gate_failures)
