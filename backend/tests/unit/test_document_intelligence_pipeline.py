import io
import pytest
from pydantic import BaseModel

from app.ingestion.grounding_verifier import GroundingVerifier, VerificationStatus
from app.ingestion.universal_file_parser import UniversalFileParser, ContentBlockType
from app.llm.schemas import ExtractedClaim


def test_universal_parser_markdown_and_tables():
    """Verify UniversalFileParser extracts clean structured tables and headings."""
    sample_text = """# Remote Work Security Policy
## Section 1: Authentication Requirements
All employees must use FIDO2 hardware security keys for VPN access.

| Role | Access Window | Approval Level |
| Admin | 24/7 | CCO |
| Contractor | 09:00-18:00 UTC | Manager |
"""
    raw_bytes = sample_text.encode("utf-8")
    parsed = UniversalFileParser.parse_structured("security_policy.md", raw_bytes)

    assert parsed.title == "Security Policy"
    assert parsed.file_type == "plain_text"
    assert len(parsed.blocks) >= 1
    assert "FIDO2" in parsed.full_text
    assert "Remote Work Security Policy" in parsed.full_text


def test_universal_parser_csv_structured():
    """Verify CSV parser correctly extracts tabular records."""
    csv_content = """Policy_ID,Policy_Name,Min_Days,Authority
POL-01,Notice Period,30,HR Director
POL-02,Probation Period,90,Team Lead
"""
    parsed = UniversalFileParser.parse_structured("policies.csv", csv_content.encode("utf-8"))

    assert parsed.file_type == "csv"
    assert "Notice Period" in parsed.full_text
    assert "HR Director" in parsed.full_text
    assert len(parsed.blocks) >= 1


def test_grounding_verifier_exact_match_and_offsets():
    """Verify deterministic character offset calculation and SHA-256 evidence hashing."""
    source_document = "Section 4.1 Notice Period: All regular full-time employees must provide at least 30 days written notice prior to departure."
    
    claim = ExtractedClaim(
        claim_text="Full-time employees must provide at least 30 days notice.",
        subject="Full-time employees",
        predicate="must_provide_notice",
        object="30 days",
        modality="MUST",
        evidence_text_span="All regular full-time employees must provide at least 30 days written notice prior to departure.",
        numeric_value=30.0,
        numeric_unit="days",
        confidence=0.98,
    )

    result = GroundingVerifier.verify_and_ground_claim(claim, source_document, section_start_offset=0)

    assert result.is_valid is True
    assert result.status == VerificationStatus.VERIFIED
    assert result.numeric_grounded is True
    assert result.verified_modality == "MUST"
    assert result.start_offset == 27
    assert result.end_offset == 27 + len(claim.evidence_text_span)
    assert len(result.evidence_hash) == 64  # SHA-256 length


def test_grounding_verifier_negation_modality_alignment():
    """Verify prohibited/forbidden actions are deterministically aligned to CANNOT."""
    source_document = "Employees cannot export unencrypted production data to personal external drives under any circumstances."

    claim = ExtractedClaim(
        claim_text="Employees may export production data.",
        subject="Employees",
        predicate="export_data",
        object="production data",
        modality="MAY",  # Candidate extraction incorrectly extracted MAY
        evidence_text_span="Employees cannot export unencrypted production data to personal external drives",
        confidence=0.95,
    )

    result = GroundingVerifier.verify_and_ground_claim(claim, source_document, section_start_offset=10)

    assert result.is_valid is True
    # Verifier must deterministically correct modality to CANNOT based on source language
    assert result.verified_modality == "CANNOT"
    assert result.start_offset == 10
    assert result.end_offset == 10 + len(claim.evidence_text_span)


def test_grounding_verifier_hallucinated_numeric_purged():
    """Verify hallucinated numbers not present in the source text are purged."""
    source_document = "The retention period for audit logs shall be maintained indefinitely."

    claim = ExtractedClaim(
        claim_text="Audit logs must be kept for 365 days.",
        subject="Audit logs",
        predicate="retention_period",
        object="365 days",
        modality="MUST",
        evidence_text_span="The retention period for audit logs shall be maintained indefinitely.",
        numeric_value=365.0,  # Hallucinated number not in source
        numeric_unit="days",
        confidence=0.95,
    )

    result = GroundingVerifier.verify_and_ground_claim(
        claim,
        source_document,
        section_start_offset=0,
        require_numeric_grounding=True,
    )

    assert result.is_valid is True
    assert result.numeric_grounded is False
    assert claim.numeric_value is None  # Purged
    assert result.status == VerificationStatus.PARTIALLY_SUPPORTED
    assert len(result.warnings) > 0


def test_grounding_verifier_unsupported_claim_dropped():
    """Verify claims without evidence in the source document are rejected."""
    source_document = "Security badges must be returned upon employment termination."

    claim = ExtractedClaim(
        claim_text="Company reimburses home internet up to $100 per month.",
        subject="Company",
        predicate="reimburse_internet",
        object="$100",
        modality="MUST",
        evidence_text_span="Company reimburses home internet up to $100 per month",
        confidence=0.95,
    )

    result = GroundingVerifier.verify_and_ground_claim(claim, source_document, section_start_offset=0)

    assert result.is_valid is False
    assert result.status == VerificationStatus.UNSUPPORTED
    assert "was not found in source section" in result.rejection_reason
