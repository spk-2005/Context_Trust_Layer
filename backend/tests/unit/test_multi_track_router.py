"""
Unit tests for Multi-Track Separation Router & Specialized Track Processors (Sprint AF-11).
Validates:
1. Document routing between Track A (Contract), Track B (Invoice), and Track C (SOC).
2. Invoice arithmetic invariants (line item total, header subtotal/tax/grand total).
3. SOC Trust Services Criteria classification and testing exception capture.
4. Zero cross-track leakage isolation from the normative policy claims graph.
"""

import pytest
from app.extraction.multi_track_router import (
    MultiTrackRouter,
    DocumentTrack,
    RoutingDecision,
)
from app.extraction.invoice_track_processor import (
    InvoiceTrackProcessor,
    InvoiceRecord,
    InvoiceLineItem,
)
from app.extraction.soc_track_processor import (
    SOCTrackProcessor,
    SOCControlStatement,
    TrustServiceCriteria,
    SOCTestResult,
)


def test_route_contract_to_track_a():
    """Verify contracts and agreements route to Track A."""
    decision = MultiTrackRouter.route_document(
        document_id="DOC-057",
        filename="Microsoft_Customer_Agreement.pdf",
        document_type="contract",
        sample_text="This Microsoft Customer Agreement is entered into between Customer and Microsoft.",
    )
    assert decision.track == DocumentTrack.TRACK_A_CONTRACT
    assert decision.schema_target == "CanonicalClaimV3"
    assert decision.confidence >= 0.95


def test_route_invoice_to_track_b():
    """Verify invoices, billing documents, and POs route to Track B."""
    decision_by_type = MultiTrackRouter.route_document(
        document_id="DOC-052",
        filename="Doc52.pdf",
        document_type="invoice",
        sample_text="INVOICE #INV-2023-8910 Subtotal: $12,450.00 Total Due: $13,570.50",
    )
    assert decision_by_type.track == DocumentTrack.TRACK_B_INVOICE
    assert decision_by_type.schema_target == "InvoiceRecord"

    decision_by_name = MultiTrackRouter.route_document(
        document_id="DOC-063",
        filename="azure_mca_billing_migration_guide.docx",
        document_type="guide",
        sample_text="This guide details transfer of billing ownership and billing invoice accounts.",
    )
    assert decision_by_name.track == DocumentTrack.TRACK_B_INVOICE
    assert decision_by_name.schema_target == "InvoiceRecord"


def test_route_soc_to_track_c():
    """Verify SOC 1, SOC 2, and ISO audit documents route to Track C."""
    decision_by_type = MultiTrackRouter.route_document(
        document_id="DOC-059",
        filename="soc2_type2_report.pdf",
        document_type="soc_report",
        sample_text="Report on Controls at a Service Organization Relevant to Security and Availability.",
    )
    assert decision_by_type.track == DocumentTrack.TRACK_C_SOC
    assert decision_by_type.schema_target == "SOCControlStatement"

    decision_by_content = MultiTrackRouter.route_document(
        document_id="DOC-080",
        filename="compliance_matrix.pdf",
        document_type="compliance",
        sample_text="Independent Service Auditor Report on Trust Services Criteria AICPA CC6.1 Testing Procedures.",
    )
    assert decision_by_content.track == DocumentTrack.TRACK_C_SOC
    assert decision_by_content.schema_target == "SOCControlStatement"


def test_invoice_arithmetic_invariant_valid():
    """Verify mathematical invariant checks pass for balanced line items and totals."""
    item1 = InvoiceLineItem(
        item_id="ITEM-001",
        description="Azure Virtual Machines (D4s v5)",
        quantity=10.0,
        unit_price=140.00,
        line_total=1400.00,
    )
    item2 = InvoiceLineItem(
        item_id="ITEM-002",
        description="Azure Storage Account Standard LRS",
        quantity=5.0,
        unit_price=20.00,
        line_total=100.00,
    )
    record = InvoiceRecord(
        document_id="DOC-052",
        subtotal=1500.00,
        tax=120.00,
        discount=20.00,
        grand_total=1600.00,
        line_items=[item1, item2],
    )
    validated = InvoiceTrackProcessor.validate_invoice_record(record)
    assert validated.all_line_items_valid is True
    assert validated.header_arithmetic_valid is True
    assert validated.validation_status == "VALIDATED"


def test_invoice_arithmetic_invariant_failure_detected():
    """Verify arithmetic discrepancy knocks out invalid invoice totals."""
    item = InvoiceLineItem(
        item_id="ITEM-001",
        description="Corrupted Unit Price Service",
        quantity=10.0,
        unit_price=100.00,
        line_total=1500.00,  # Expected 1000.00, discrepancy is 500.00
    )
    record = InvoiceRecord(
        document_id="DOC-052",
        subtotal=1500.00,
        tax=100.00,
        discount=0.00,
        grand_total=1800.00,  # Expected 1600.00
        line_items=[item],
    )
    validated = InvoiceTrackProcessor.validate_invoice_record(record)
    assert validated.all_line_items_valid is False
    assert validated.header_arithmetic_valid is False
    assert validated.validation_status == "ARITHMETIC_ERROR"
    assert item.arithmetic_discrepancy == 500.00


def test_invoice_text_parser():
    """Verify text parsing extracts fields and validates automatically."""
    sample_invoice_text = """
    INVOICE NUMBER: INV-2023-45612
    Invoice Date: October 15, 2023
    Payment Due: November 14, 2023
    Terms: Net 30 days
    Subtotal: $4,000.00
    Tax: $320.00
    Total Due: $4,320.00
    """
    parsed = InvoiceTrackProcessor.parse_invoice_text("DOC-052", sample_invoice_text)
    assert parsed.document_id == "DOC-052"
    assert parsed.invoice_number == "INV-2023-45612"
    assert parsed.subtotal == 4000.00
    assert parsed.tax == 320.00
    assert parsed.grand_total == 4320.00
    assert parsed.validation_status == "VALIDATED"
    assert len(parsed.line_items) >= 1


def test_soc_control_statement_criteria_classification():
    """Verify AICPA criteria mapping and exception extraction."""
    sec_control = SOCTrackProcessor.parse_control_statement(
        document_id="DOC-059",
        raw_text="CC6.1 Access controls and encryption key management are enforced to protect customer data.",
    )
    assert sec_control.control_id == "CC6.1"
    assert sec_control.trust_service_criteria == TrustServiceCriteria.SECURITY
    assert sec_control.test_results == SOCTestResult.NO_EXCEPTIONS

    avail_control = SOCTrackProcessor.parse_control_statement(
        document_id="DOC-059",
        raw_text="CC7.2 Disaster recovery, backup, and system uptime replication procedures were evaluated.",
    )
    assert avail_control.trust_service_criteria == TrustServiceCriteria.AVAILABILITY

    priv_control = SOCTrackProcessor.parse_control_statement(
        document_id="DOC-059",
        raw_text="P1.1 Data privacy consent and GDPR personal data erasure requests are processed within 30 days. Exception noted in 1 out of 45 samples.",
    )
    assert priv_control.trust_service_criteria == TrustServiceCriteria.PRIVACY
    assert priv_control.test_results == SOCTestResult.EXCEPTION_NOTED
    assert priv_control.exception_details is not None


def test_filter_leakage_prevents_invoice_contamination():
    """Verify zero financial leakage into the Track A normative policy graph."""
    claims = [
        {
            "claim_id": "CLM-001",
            "subject": "Customer",
            "object": "Customer may terminate agreement for convenience",
            "evidence_quote": "Customer may terminate this Agreement without cause upon 60 days written notice.",
        },
        {
            "claim_id": "CLM-002",
            "subject": "Invoice",
            "object": "$ 14,250.00 payable upon receipt",
            "evidence_quote": "Invoice Total: $ 14,250.00 due within 30 days.",
        },
    ]

    clean, quarantined = MultiTrackRouter.filter_leakage(claims, DocumentTrack.TRACK_A_CONTRACT)
    assert len(clean) == 1
    assert clean[0]["claim_id"] == "CLM-001"
    assert len(quarantined) == 1
    assert quarantined[0]["claim_id"] == "CLM-002"
