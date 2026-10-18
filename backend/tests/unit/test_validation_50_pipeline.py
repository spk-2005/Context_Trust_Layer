"""
Unit tests for Sprint AD 50-Document Validation Engine.
"""

from pathlib import Path
import pytest

from app.ingestion.universal_file_parser import ContentBlock, ContentBlockType, ParsedDocument
from research.validation_50.init_manifest import detect_document_type
from research.validation_50.run_validation import ClaimAuditor, ParsingAuditor


@pytest.mark.fast
@pytest.mark.unit
def test_detect_document_type():
    assert detect_document_type("customer_refund_policy_2026.pdf") == "refund_policy"
    assert detect_document_type("employee_leave_handbook.docx") == "hr_policy"
    assert detect_document_type("master_vendor_agreement.pdf") == "contract"
    assert detect_document_type("invoice_inv_9988.pdf") == "invoice"
    assert detect_document_type("soc2_hipaa_compliance_rules.txt") == "regulatory_compliance"
    assert detect_document_type("scanned_receipt_image.pdf") == "scanned_document"
    assert detect_document_type("pricing_schedule_table.pdf") == "table_heavy"
    assert detect_document_type("general_guidelines.txt") == "general_policy"


@pytest.mark.fast
@pytest.mark.unit
def test_parsing_auditor_pass_and_failure_detection():
    # Clean parsed document
    clean_doc = ParsedDocument(
        filename="policy.pdf",
        title="Policy",
        file_type="pdf",
        content_hash="abc",
        full_text="# Cancellation Policy\n\nCustomers may cancel their subscription within 14 days of purchase.",
        raw_text="...",
        blocks=[
            ContentBlock(id="b1", block_type=ContentBlockType.HEADING, text="# Cancellation Policy", raw_text="# Cancellation Policy"),
            ContentBlock(id="b2", block_type=ContentBlockType.PARAGRAPH, text="Customers may cancel their subscription within 14 days of purchase.", raw_text="..."),
        ],
        tables=[],
        metadata={"file_size": 100},
    )
    clean_audit = ParsingAuditor.audit_document("DOC-051", "policy.pdf", clean_doc)
    assert clean_audit["parsing_status"] == "PASS"
    assert clean_audit["all_issues_count"] == 0

    # Corrupt document with null bytes
    corrupt_doc = ParsedDocument(
        filename="corrupt.pdf",
        title="Corrupt",
        file_type="pdf",
        content_hash="def",
        full_text="Corrupt \x00\x00 data",
        raw_text="...",
        blocks=[],
        tables=[],
        metadata={"file_size": 20},
    )
    corrupt_audit = ParsingAuditor.audit_document("DOC-052", "corrupt.pdf", corrupt_doc)
    assert corrupt_audit["parsing_status"] == "FAIL"
    assert any("Null byte" in i for i in corrupt_audit["major_issues"])


@pytest.mark.fast
@pytest.mark.unit
def test_claim_auditor_extracts_and_scores_claims():
    doc = ParsedDocument(
        filename="vendor_sla.pdf",
        title="Vendor SLA",
        file_type="pdf",
        content_hash="ghi",
        full_text="4.1 Indemnity. The Vendor shall fully indemnify and hold harmless the Client against all claims.",
        raw_text="...",
        blocks=[
            ContentBlock(
                id="b1",
                block_type=ContentBlockType.PARAGRAPH,
                text="4.1 Indemnity. The Vendor shall fully indemnify and hold harmless the Client against all claims.",
                raw_text="...",
            )
        ],
        tables=[],
        metadata={"file_size": 200},
    )

    audit = ClaimAuditor.audit_claims("DOC-053", "vendor_sla.pdf", "contract", doc)
    assert audit["claim_counts"]["candidate_claims"] >= 1
    assert audit["claim_counts"]["valid"] >= 1
    assert audit["metrics"]["claim_precision"] > 0.0
    assert audit["metrics"]["evidence_supported_rate"] == 1.0