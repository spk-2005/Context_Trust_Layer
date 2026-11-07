"""
Unit tests for Phase 6: Exact Evidence Matching and Reliable Claim Validation.

Verifies:
1. Northwind refund scenario: video-course refund does not link to general digital goods clause.
2. Correct claim with missing evidence yields INSUFFICIENT_EVIDENCE (not CONTRADICTED).
3. Direct contradiction yields CONTRADICTED.
4. Condition omitted from claim yields NEEDS_REVIEW with missing_conditions.
5. Exception omitted from claim yields NEEDS_REVIEW with missing_exceptions.
6. Multi-block support yields SUPPORTED across rule + condition + definition units.
7. Table value linked to wrong header yields NEEDS_REVIEW.
8. Older versus newer source versions handled gracefully without false contradiction.
"""

import uuid
from datetime import datetime, timezone
import pytest

from app.extraction.models import CandidateClaim, TableGridBinding
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceUnit,
    ExtractionStatus,
    ParsedEvidenceUnit,
    SourceLocator,
)
from app.validation_gate.evidence_validator import ReliableClaimEvidenceValidator
from app.validation_gate.models import (
    ClaimValidationStatus,
)


def _make_candidate(
    subject: str,
    predicate: str,
    object_: str,
    claim_text: str,
    evidence_text_span: str = "",
    conditions: list = None,
    exceptions: list = None,
    value: any = None,
    unit: str = None,
    modality: str = "POLICY_FACT",
    table_binding: TableGridBinding = None,
    source_version: str = "v1.0",
    extraction_status: str = "success",
    unit_id: str = "unit-1",
    evidence_unit_ids: list = None,
) -> CandidateClaim:
    return CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id=unit_id,
        asset_id="asset-test",
        claim_text=claim_text,
        subject=subject,
        predicate=predicate,
        object_=object_,
        evidence_text_span=evidence_text_span or claim_text,
        conditions=conditions or [],
        exceptions=exceptions or [],
        value=value,
        unit=unit,
        modality=modality,
        table_binding=table_binding,
        source_version=source_version,
        extraction_status=extraction_status,
        evidence_unit_ids=evidence_unit_ids or ([unit_id] if unit_id else []),
    )


def test_northwind_refund_safeguard():
    """
    Northwind refund scenario:
    Unit 1: Digital goods are non-refundable.
    Unit 2: Video courses are eligible for a full refund within 7 days, provided less than 20% viewed.

    Candidate claim: Video courses eligible for refund within 7 days, <20% viewed.
    Must retrieve Unit 2 and NOT link to Unit 1 (topical contamination safeguard).
    Must validate as SUPPORTED.
    """
    unit_digital_goods = EvidenceUnit.create(
        asset_id="northwind_policy",
        source_id="northwind_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="All digital goods, software licenses, and digital assets are strictly non-refundable once delivered.",
        normalized_content="All digital goods, software licenses, and digital assets are strictly non-refundable once delivered.",
        locator=SourceLocator(source_type="docx", section="4.1 Digital Products"),
        sequence_index=1,
    )

    unit_video_course = EvidenceUnit.create(
        asset_id="northwind_policy",
        source_id="northwind_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Video courses are eligible for a full refund within 7 days of purchase, provided less than 20% of the course content has been viewed.",
        normalized_content="Video courses are eligible for a full refund within 7 days of purchase, provided less than 20% of the course content has been viewed.",
        locator=SourceLocator(source_type="docx", section="4.2 Video Courses"),
        sequence_index=2,
    )

    evidence_units = [unit_digital_goods, unit_video_course]

    claim = _make_candidate(
        subject="Video courses",
        predicate="are eligible for",
        object_="full refund within 7 days",
        claim_text="Video courses are eligible for a full refund within 7 days of purchase, provided less than 20% of the course content has been viewed.",
        evidence_text_span="Video courses are eligible for a full refund within 7 days of purchase, provided less than 20% of the course content has been viewed.",
        conditions=["less than 20% of the course content has been viewed"],
        value=7,
        unit="days",
        unit_id=unit_video_course.unit_id,
        evidence_unit_ids=[unit_video_course.unit_id],
    )

    # 1. Retrieval Safeguard Check:
    retrieved = ReliableClaimEvidenceValidator.retrieve_candidate_evidence(claim, evidence_units)
    retrieved_ids = [getattr(u, "unit_id", None) for u in retrieved]
    assert unit_video_course.unit_id in retrieved_ids
    assert unit_digital_goods.unit_id not in retrieved_ids, "Topical cross-contamination: digital goods clause should not link to video courses"

    # 2. Validation Check:
    report = ReliableClaimEvidenceValidator.validate_claim(claim, evidence_units)
    assert report.validation_status == ClaimValidationStatus.SUPPORTED
    assert unit_video_course.unit_id in report.linked_evidence_ids
    assert unit_digital_goods.unit_id not in report.linked_evidence_ids
    assert len(report.missing_conditions) == 0


def test_missing_evidence_yields_insufficient_evidence():
    """
    Correct claim with missing evidence must yield INSUFFICIENT_EVIDENCE,
    not CONTRADICTED or generic REJECT.
    """
    claim = _make_candidate(
        subject="Annual incentive bonus",
        predicate="is disbursed on",
        object_="March 15",
        claim_text="Annual incentive bonus is disbursed on March 15.",
        unit_id="non-existent-unit",
        evidence_unit_ids=["non-existent-unit"],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(claim, evidence_units=[])
    assert report.validation_status == ClaimValidationStatus.INSUFFICIENT_EVIDENCE
    assert "Missing citation is not proof of contradiction" in report.reasoning_summary


def test_direct_contradiction_yields_contradicted():
    """
    Direct contradiction within the same version and scope must yield CONTRADICTED.
    """
    unit_mfa = EvidenceUnit.create(
        asset_id="sec-policy",
        source_id="sec_doc",
        source_type="pdf",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Contractors are strictly prohibited from accessing internal systems without hardware MFA tokens.",
        normalized_content="Contractors are strictly prohibited from accessing internal systems without hardware MFA tokens.",
        locator=SourceLocator(source_type="pdf", page=3),
        sequence_index=1,
    )

    claim_contradictory = _make_candidate(
        subject="Contractors",
        predicate="may access",
        object_="internal systems without hardware MFA tokens",
        claim_text="Contractors may access internal systems without hardware MFA tokens.",
        evidence_text_span="Contractors may access internal systems without hardware MFA tokens.",
        modality="PERMITTED",
        unit_id=unit_mfa.unit_id,
        evidence_unit_ids=[unit_mfa.unit_id],
    )

    # Competing historical/existing claim asserting the PROHIBITED rule
    existing_claim = _make_candidate(
        subject="Contractors",
        predicate="are prohibited from",
        object_="accessing internal systems without hardware MFA tokens",
        claim_text="Contractors are strictly prohibited from accessing internal systems without hardware MFA tokens.",
        modality="PROHIBITED",
        unit_id=unit_mfa.unit_id,
        evidence_unit_ids=[unit_mfa.unit_id],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(
        claim_contradictory,
        evidence_units=[unit_mfa],
        historical_claims=[existing_claim],
    )
    assert report.validation_status == ClaimValidationStatus.CONTRADICTED
    assert "Deontic conflict" in report.reasoning_summary


def test_condition_omitted_yields_needs_review():
    """
    When source evidence specifies explicit conditions but the claim omits them,
    the claim validation status must be NEEDS_REVIEW with missing_conditions populated.
    """
    unit_returns = EvidenceUnit.create(
        asset_id="store-policy",
        source_id="store_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Equipment returns are accepted within 30 days of delivery, provided items are returned in original packaging.",
        normalized_content="Equipment returns are accepted within 30 days of delivery, provided items are returned in original packaging.",
        locator=SourceLocator(source_type="docx", section="Returns"),
        sequence_index=1,
    )

    # Claim omits "provided items are returned in original packaging"
    claim_incomplete = _make_candidate(
        subject="Equipment returns",
        predicate="are accepted within",
        object_="30 days of delivery",
        claim_text="Equipment returns are accepted within 30 days of delivery.",
        evidence_text_span="Equipment returns are accepted within 30 days of delivery",
        conditions=[],  # OMITTED!
        value=30,
        unit="days",
        unit_id=unit_returns.unit_id,
        evidence_unit_ids=[unit_returns.unit_id],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(claim_incomplete, evidence_units=[unit_returns])
    assert report.validation_status == ClaimValidationStatus.NEEDS_REVIEW
    assert len(report.missing_conditions) > 0
    assert any("original packaging" in mc for mc in report.missing_conditions)


def test_exception_omitted_yields_needs_review():
    """
    When source evidence specifies explicit exclusions/exceptions but the claim omits them,
    the claim validation status must be NEEDS_REVIEW with missing_exceptions populated.
    """
    unit_cancellations = EvidenceUnit.create(
        asset_id="hardware-policy",
        source_id="hardware_manual",
        source_type="pdf",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="All enterprise hardware orders can be cancelled before shipping, except custom-configured rack servers.",
        normalized_content="All enterprise hardware orders can be cancelled before shipping, except custom-configured rack servers.",
        locator=SourceLocator(source_type="pdf", page=12),
        sequence_index=1,
    )

    # Claim omits the exception
    claim_omits_exc = _make_candidate(
        subject="Enterprise hardware orders",
        predicate="can be cancelled before",
        object_="shipping",
        claim_text="All enterprise hardware orders can be cancelled before shipping.",
        evidence_text_span="All enterprise hardware orders can be cancelled before shipping",
        exceptions=[],  # OMITTED!
        unit_id=unit_cancellations.unit_id,
        evidence_unit_ids=[unit_cancellations.unit_id],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(claim_omits_exc, evidence_units=[unit_cancellations])
    assert report.validation_status == ClaimValidationStatus.NEEDS_REVIEW
    assert len(report.missing_exceptions) > 0
    assert any("custom-configured rack servers" in me for me in report.missing_exceptions)


def test_multi_block_support_yields_supported():
    """
    Combined meaning across multiple evidence units:
    Unit A: Rule statement
    Unit B: Condition / duration
    Unit C: Definition
    Claim combines all three and should be validated as SUPPORTED with multi_block relationship.
    """
    unit_a = EvidenceUnit.create(
        asset_id="leave-policy",
        source_id="hr_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Eligible employees are entitled to bereavement leave.",
        normalized_content="Eligible employees are entitled to bereavement leave.",
        locator=SourceLocator(source_type="docx", section="Leave"),
        sequence_index=1,
    )

    unit_b = EvidenceUnit.create(
        asset_id="leave-policy",
        source_id="hr_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Bereavement leave duration is up to 5 consecutive business days.",
        normalized_content="Bereavement leave duration is up to 5 consecutive business days.",
        locator=SourceLocator(source_type="docx", section="Leave Duration"),
        sequence_index=2,
    )

    unit_c = EvidenceUnit.create(
        asset_id="leave-policy",
        source_id="hr_manual",
        source_type="docx",
        block_type="paragraph",
        content_role=ContentRole.DEFINITION,
        raw_content="'Eligible employee' refers to active regular staff with 6+ months service.",
        normalized_content="'Eligible employee' refers to active regular staff with 6+ months service.",
        locator=SourceLocator(source_type="docx", section="Glossary"),
        sequence_index=3,
    )

    evidence_units = [unit_a, unit_b, unit_c]

    claim = _make_candidate(
        subject="Active regular staff",
        predicate="are entitled to",
        object_="up to 5 consecutive business days of bereavement leave",
        claim_text="Active regular staff eligible employees are entitled to bereavement leave of up to 5 consecutive business days.",
        evidence_text_span="Eligible employees are entitled to bereavement leave. Bereavement leave duration is up to 5 consecutive business days.",
        unit_id=unit_a.unit_id,
        evidence_unit_ids=[unit_a.unit_id, unit_b.unit_id, unit_c.unit_id],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(claim, evidence_units)
    assert report.validation_status == ClaimValidationStatus.SUPPORTED
    assert len(report.linked_evidence_ids) >= 2
    assert unit_a.unit_id in report.linked_evidence_ids
    assert report.evidence_relationship in ("multi_block", "rule_with_definition")


def test_table_value_linked_to_wrong_header_yields_needs_review():
    """
    When table value is mapped to the wrong column header (e.g. shifted column),
    validation status must be NEEDS_REVIEW.
    """
    table_unit = EvidenceUnit.create(
        asset_id="leave-matrix",
        source_id="hr_matrix",
        source_type="xlsx",
        block_type="table",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Tier | Probationers | Confirmed Staff\nGrade 1 | 10 days | 20 days",
        normalized_content="Tier: Grade 1, Probationers: 10 days, Confirmed Staff: 20 days",
        structured_data={
            "table_id": "tbl-leave-1",
            "headers": ["Tier", "Probationers", "Confirmed Staff"],
            "grid": [
                {"Tier": "Grade 1", "Probationers": "10 days", "Confirmed Staff": "20 days"}
            ]
        },
        locator=SourceLocator(source_type="xlsx", table_id="tbl-leave-1"),
        sequence_index=1,
    )

    # Claim erroneously binds "20 days" to "Probationers" (when it actually belongs to "Confirmed Staff")
    wrong_table_binding = TableGridBinding(
        table_id="tbl-leave-1",
        row_key="Grade 1",
        column_header="Probationers",
        cell_value="20 days",
        normalized_value=20,
        normalized_unit="days",
    )

    claim = _make_candidate(
        subject="Grade 1 Probationers",
        predicate="receive annual leave of",
        object_="20 days",
        claim_text="Grade 1 Probationers receive annual leave of 20 days.",
        table_binding=wrong_table_binding,
        unit_id=table_unit.unit_id,
        evidence_unit_ids=[table_unit.unit_id],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(claim, evidence_units=[table_unit])
    assert report.validation_status == ClaimValidationStatus.NEEDS_REVIEW
    assert any("Confirmed Staff" in w or "belongs to column" in w or "mismatch" in w.lower() for w in report.warnings)


def test_older_vs_newer_source_version_no_false_contradiction():
    """
    Version Lineage:
    v1.0 policy: 14 days
    v2.0 policy: 30 days
    Evaluating v2.0 claim must NOT treat v1.0 as a contradiction.
    It should recognize version progression and validate as SUPPORTED.
    """
    unit_v2 = EvidenceUnit.create(
        asset_id="refund-doc-v2",
        source_id="refund_source",
        source_type="pdf",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content="Standard refund window is 30 days from purchase date.",
        normalized_content="Standard refund window is 30 days from purchase date.",
        source_version="v2.0",
        locator=SourceLocator(source_type="pdf", page=1),
        sequence_index=1,
    )

    claim_v2 = _make_candidate(
        subject="Standard refund window",
        predicate="is",
        object_="30 days from purchase date",
        claim_text="Standard refund window is 30 days from purchase date.",
        evidence_text_span="Standard refund window is 30 days from purchase date.",
        value=30,
        unit="days",
        source_version="v2.0",
        unit_id=unit_v2.unit_id,
        evidence_unit_ids=[unit_v2.unit_id],
    )

    # Historical claim from v1.0
    claim_v1_historical = _make_candidate(
        subject="Standard refund window",
        predicate="is",
        object_="14 days from purchase date",
        claim_text="Standard refund window is 14 days from purchase date.",
        value=14,
        unit="days",
        source_version="v1.0",
        unit_id="unit-policy-v1",
        evidence_unit_ids=["unit-policy-v1"],
    )

    report = ReliableClaimEvidenceValidator.validate_claim(
        claim_v2,
        evidence_units=[unit_v2],
        historical_claims=[claim_v1_historical],
    )

    assert report.validation_status == ClaimValidationStatus.SUPPORTED
    assert report.validation_status != ClaimValidationStatus.CONTRADICTED
    assert any("superseded" in w.lower() for w in report.warnings)
