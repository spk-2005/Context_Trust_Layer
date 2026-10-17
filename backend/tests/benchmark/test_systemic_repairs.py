"""
Negative regression tests for universal systemic repairs in Sprint S.
Verifies that structural layout, clause inheritance, and domain routing bugs
are resolved at the class level rather than through per-document hacks.
"""

import pytest
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.subject_normalizer import SubjectNormalizer
from app.normalization.document_restructurer import DocumentSemanticRestructurer

def test_payment_due_date_does_not_corrupt_to_return_window():
    """Negative Test: Payment terms with 'within 30 days' must NOT map to has_return_window."""
    pred, obj, mod = DomainRuleExtractor.normalize_predicate_and_modality(
        raw_pred="due",
        raw_pred_obj="within 30 days from date of invoice",
        clean_sentence="Payment is due within 30 days from date of invoice.",
        raw_modal="is",
        current_modality="OBLIGATION"
    )
    assert pred == "has_due_date_period", f"Expected has_due_date_period, got {pred}"
    assert pred != "has_return_window"

def test_late_payment_fee_extracts_administrative_fee():
    """Negative Test: Late payment penalties must map to fee rules, not generic validity."""
    pred, obj, mod = DomainRuleExtractor.normalize_predicate_and_modality(
        raw_pred="subject",
        raw_pred_obj="to fees of 5% per month",
        clean_sentence="Late payment is subject to fees of 5% per month.",
        raw_modal="is",
        current_modality="PERMISSION"
    )
    assert pred == "may_apply_administration_fee", f"Expected may_apply_administration_fee, got {pred}"

def test_currency_amounts_never_become_table_headers():
    """Negative Test: Candidate cells with pure currency amounts must be rejected as table headers."""
    invalid_header = ["Total", "$85.00"]
    is_valid = DocumentSemanticRestructurer.is_valid_table_header(invalid_header)
    assert is_valid is False, "A cell with currency amount '$85.00' must not be accepted as a table column header"

def test_section_numbers_resolve_to_operative_actor():
    """Negative Test: Dotted section numbers must resolve to the operative actor from context."""
    norm_subj, valid = SubjectNormalizer.normalize(
        raw_subject="3.6.3.2",
        context="3.6.3.2 The Vendor shall not commence to construct homes"
    )
    assert norm_subj == "Vendor" or norm_subj == "The Vendor", f"Expected Vendor entity, got {norm_subj}"
    assert not norm_subj.startswith("3."), f"Section number was not resolved to actor: {norm_subj}"
