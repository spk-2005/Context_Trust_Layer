"""
Unit Tests for Sprint AF-8 Independent Evidence Verification Engine
"""

from pathlib import Path
import pytest

from app.extraction.independent_evidence_verifier import (
    DocumentPage,
    EvidenceVerificationStatus,
    IndependentEvidenceVerifier,
)


class TestIndependentEvidenceVerifier:

    @pytest.fixture
    def mock_document_pages(self):
        text_p1 = (
            "MICROSOFT CUSTOMER AGREEMENT\n\n"
            "1. License Grants\n"
            "Microsoft grants Customer a nonexclusive and limited license to use the Products ordered "
            "as provided in this Agreement.\n\n"
            "2. Reservation of Rights\n"
            "Microsoft reserves all rights not expressly granted in this Agreement."
        )
        text_p2 = (
            "3. Termination\n"
            "Either party may terminate this Agreement without cause upon 60 days prior written notice.\n\n"
            "4. Remedies for Breach\n"
            "Either party may terminate for material breach on 30 calendar days notice if uncured."
        )
        return [
            DocumentPage(page_number=1, text=text_p1, char_offset_start=0, char_offset_end=len(text_p1)),
            DocumentPage(page_number=2, text=text_p2, char_offset_start=len(text_p1) + 1, char_offset_end=len(text_p1) + 1 + len(text_p2)),
        ]

    def test_verify_exact_quote_match_success(self, mock_document_pages):
        quote = "Microsoft grants Customer a nonexclusive and limited license to use the Products ordered"
        report = IndependentEvidenceVerifier.verify_claim_evidence(
            claim_id="CLM-001",
            document_id="DOC-057",
            evidence_quote=quote,
            reported_page=1,
            pages=mock_document_pages,
        )
        assert report.span_exists is True
        assert report.verification_status == EvidenceVerificationStatus.EVIDENCE_VERIFIED
        assert report.page_match is True
        assert report.actual_page == 1
        assert report.char_start >= 0
        assert report.char_end > report.char_start
        assert "License Grants" in report.enclosing_clause_text

    def test_verify_whitespace_tolerance(self, mock_document_pages):
        # Quote with linebreaks and irregular spacing
        quote = "Microsoft   grants\nCustomer a nonexclusive and limited license"
        report = IndependentEvidenceVerifier.verify_claim_evidence(
            claim_id="CLM-002",
            document_id="DOC-057",
            evidence_quote=quote,
            reported_page=1,
            pages=mock_document_pages,
        )
        assert report.span_exists is True
        assert report.verification_status == EvidenceVerificationStatus.EVIDENCE_VERIFIED
        assert report.actual_page == 1

    def test_verify_page_drift_detection(self, mock_document_pages):
        # Quote is actually on page 2, but claim reports page 1
        quote = "Either party may terminate this Agreement without cause upon 60 days prior written notice."
        report = IndependentEvidenceVerifier.verify_claim_evidence(
            claim_id="CLM-003",
            document_id="DOC-057",
            evidence_quote=quote,
            reported_page=1,
            pages=mock_document_pages,
        )
        assert report.span_exists is True
        assert report.verification_status == EvidenceVerificationStatus.EVIDENCE_PARTIAL
        assert report.page_match is False
        assert report.actual_page == 2
        assert any("drift" in r.lower() or "reported page" in r.lower() for r in report.failure_reasons)

    def test_verify_missing_quote_fails(self, mock_document_pages):
        quote = "Customer must pay an arbitrary penalty fee of one million dollars."
        report = IndependentEvidenceVerifier.verify_claim_evidence(
            claim_id="CLM-004",
            document_id="DOC-057",
            evidence_quote=quote,
            reported_page=1,
            pages=mock_document_pages,
        )
        assert report.span_exists is False
        assert report.verification_status == EvidenceVerificationStatus.EVIDENCE_FAILED
        assert report.actual_page is None
        assert len(report.failure_reasons) > 0

    def test_real_doc057_pdf_byte_verification(self):
        doc_path = Path("research/validation_50/raw_documents/Microsoft/Contracts/Microsoft Customer Agreement.pdf")
        if not doc_path.exists():
            pytest.skip("DOC-057 raw document not found on disk")

        pages = IndependentEvidenceVerifier.extract_document_pages(doc_path)
        assert len(pages) >= 10, f"Expected at least 10 pages, got {len(pages)}"

        # Ground truth quote from Section 1.g
        quote = "Customer may only transfer fully-paid, perpetual licenses to (1) an Affiliate"
        report = IndependentEvidenceVerifier.verify_claim_evidence(
            claim_id="CLM-DOC057-012",
            document_id="DOC-057",
            evidence_quote=quote,
            reported_page=2,
            pages=pages,
        )
        assert report.span_exists is True
        assert report.actual_page == 2
        assert report.verification_status in (
            EvidenceVerificationStatus.EVIDENCE_VERIFIED,
            EvidenceVerificationStatus.EVIDENCE_PARTIAL,
        )
