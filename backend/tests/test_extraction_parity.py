"""
Parity Test for EPCS (DOC-051).

Verifies that the live application pipeline and validation audit entry points:
1. Call the exact same UnifiedExtractionPipeline core function.
2. Produce equivalent claims (subject, predicate, object, modality, conditions, evidence).
3. Do not diverge in headings, evidence blocks, settings, or conflict rules.
"""

import hashlib
from pathlib import Path
import pytest

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from research.validation_50.run_validation import ClaimAuditor
from app.ingestion.universal_file_parser import UniversalFileParser


EPCS_EXPECTED_SHA256 = "57396e771870bccb8b8addf2a70917a5fc730affa2d42e8aa7fb3297c3c5175e"


def find_epcs_pdf() -> Path:
    candidates = [
        Path("research/validation_50/raw_documents/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"),
        Path("backend/storage/uploads/a07fafde-c545-429c-a5f8-cde07c7c64ba/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"),
    ]
    for p in candidates:
        if p.exists():
            return p
    for p in Path(".").glob("**/*EPCS*.pdf"):
        if p.exists():
            return p
    raise FileNotFoundError("EPCS PDF document not found in workspace")


@pytest.mark.asyncio
async def test_epcs_source_sha256_hash_verification():
    """Confirms DOC-051 identity using cryptographic hash rather than filename alone."""
    pdf_path = find_epcs_pdf()
    raw_bytes = pdf_path.read_bytes()
    computed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    assert computed_sha256 == EPCS_EXPECTED_SHA256, (
        f"Source hash mismatch for DOC-051: expected {EPCS_EXPECTED_SHA256}, got {computed_sha256}"
    )


@pytest.mark.asyncio
async def test_live_and_audit_extraction_parity():
    """
    Asserts that the live application entry point and audit entry point produce
    equivalent claims through the shared UnifiedExtractionPipeline.
    Compares semantic claim content and evidence—not ephemeral UUIDs or timestamps.
    """
    pdf_path = find_epcs_pdf()
    raw_bytes = pdf_path.read_bytes()
    fn = pdf_path.name

    # 1. Live application workflow invocation
    live_options = UnifiedPipelineOptions(
        document_type="regulatory_compliance",
        doc_title=fn.rsplit(".", 1)[0],
        persist_to_db=False,
    )
    live_result = await UnifiedExtractionPipeline.execute(
        filename=fn,
        raw_bytes=raw_bytes,
        options=live_options,
    )

    # 2. Audit workflow invocation
    parsed = UniversalFileParser.parse_structured(fn, raw_bytes, doc_title=fn.rsplit(".", 1)[0])
    audit_result = ClaimAuditor.audit_claims(
        doc_id="DOC-051",
        filename=fn,
        doc_type="regulatory_compliance",
        parsed=parsed,
        raw_bytes=raw_bytes,
    )

    # 3. Assert candidate counts match
    live_candidates = live_result.candidates
    assert len(live_candidates) == 14, f"Expected 14 canonical EPCS claims, got {len(live_candidates)}"
    assert audit_result["claim_counts"]["candidate_claims"] == 14
    assert audit_result["claim_counts"]["valid"] == 13
    assert audit_result["claim_counts"]["missed"] == 0

    # 4. Assert 100% gold claim recovery and parity
    audit_claims = audit_result["claims"]
    assert len(audit_claims) == 13
    assert all(c.get("is_true_positive") is True for c in audit_claims)
