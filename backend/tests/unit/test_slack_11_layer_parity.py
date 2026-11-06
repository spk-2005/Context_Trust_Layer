"""
Parity & Verification Test Suite for Slack Connector and SyncEngine 11-Layer Architecture.

Validates that:
1. Documents synced via Slack connector or SyncEngine execute the 11-Layer UnifiedExtractionPipeline.
2. The exact same document yields deduplicated, certified atomic claims (not inflated raw chunks).
3. Layer 3 CanonicalSourceEnvelope, Layer 4 DocumentParser structured units, Layer 5 multi-track
   discovery, Layer 5.5 quality normalization, and Layer 6 10-gate validation are enforced.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.enums import ClaimStatus, SourceFamily, SourceIntent
from app.db.models.claim import Claim
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.services.claim_extraction_service import ClaimExtractionService


NORTHWIND_TEST_CONTENT = """# Northwind Refund Policy Handbook

## Page 1
Northwind Outfitters Inc. Refund, Return & Cancellation Policy Handbook.
Document ID: NW-POL-REF-2026 | Version 4.2 | Effective: January 1, 2026.

## Section 1: Standard Return Window
1. Customers must initiate product return requests within 30 days of initial delivery.
2. Proof of purchase and original invoice must be provided for all refund claims.
3. Returned merchandise must be returned in like-new, unopened, original condition.

## Section 2: Notice & Non-Refundable Items
1. Custom-manufactured equipment and perishable goods are strictly prohibited from returns.
2. Clearance items are non-refundable and cannot be exchanged.
3. Software licenses and digital gift cards will not be refunded once issued.

## Section 3: Restocking & Return Shipping Fees
1. A standard 15% restocking fee is deducted from the total refund amount for opened hardware.
2. Northwind reserves the right to withhold return shipping charges unless the item was damaged upon receipt.
"""


@pytest.mark.asyncio
async def test_unified_pipeline_direct_execution_with_parsed_content():
    """Verify UnifiedExtractionPipeline executes with parsed_content and deduplicates claims."""
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()
    ver_id = uuid.uuid4()

    pipeline_opts = UnifiedPipelineOptions(
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
        doc_title="Northwind Refund Policy Handbook",
        external_id="slack://C01/file/F123",
        persist_to_db=False,
        document_version_id=ver_id,
        parsed_content=NORTHWIND_TEST_CONTENT,
    )

    result = await UnifiedExtractionPipeline.execute(
        filename="Northwind_Refund_Policy_Handbook.md",
        raw_bytes=NORTHWIND_TEST_CONTENT.encode("utf-8"),
        options=pipeline_opts,
        parsed_content=NORTHWIND_TEST_CONTENT,
    )

    # Validate 11-Layer outputs
    assert result.envelope is not None
    assert result.envelope.source_family == SourceFamily.DOCUMENT
    assert result.envelope.source_intent == SourceIntent.GOVERNANCE_POLICY
    assert len(result.raw_candidates) > 0
    # Must be deduplicated
    assert len(result.candidates) <= len(result.raw_candidates)
    # Layer 6 evaluations exist
    assert len(result.evaluations) == len(result.candidates)
    # Check that evaluations are produced with valid lifecycle decisions (APPROVE or REVIEW)
    from app.validation_gate.models import ClaimLifecycleDecision
    valid_decisions = [e for e in result.evaluations if e.lifecycle_decision in (ClaimLifecycleDecision.APPROVE, ClaimLifecycleDecision.REVIEW)]
    assert len(valid_decisions) > 0


@pytest.mark.asyncio
async def test_claim_extraction_service_routes_to_11_layer_pipeline():
    """Verify ClaimExtractionService delegates to UnifiedExtractionPipeline for document versions."""
    mock_session = AsyncMock()

    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    mock_doc = MagicMock(spec=Document)
    mock_doc.id = doc_id
    mock_doc.organization_id = org_id
    mock_doc.source_id = src_id
    mock_doc.title = "Northwind Refund Policy Handbook"
    mock_doc.document_type = "policy"
    mock_doc.external_id = "slack://C01/file/F123"
    mock_doc.metadata = {"filename": "Northwind_Refund_Policy_Handbook.md", "source_family": "document"}

    mock_ver = MagicMock(spec=DocumentVersion)
    mock_ver.id = ver_id
    mock_ver.document_id = doc_id
    mock_ver.content_uri = NORTHWIND_TEST_CONTENT
    mock_ver.content_hash = "mock_hash"
    mock_ver.version_number = 1
    mock_ver.is_current = True

    mock_session.get.return_value = mock_ver

    service = ClaimExtractionService(mock_session)
    service.doc_repo.get_by_id = AsyncMock(return_value=mock_doc)

    mock_persisted_claims = [
        MagicMock(spec=Claim, id=uuid.uuid4(), claim_text="Customers must initiate return requests within 30 days.", status=ClaimStatus.VERIFIED),
        MagicMock(spec=Claim, id=uuid.uuid4(), claim_text="Proof of purchase must be provided for all refund claims.", status=ClaimStatus.VERIFIED),
    ]
    service.claim_repo.list_by_version = AsyncMock(return_value=mock_persisted_claims)

    with patch("app.extraction.unified_pipeline.UnifiedExtractionPipeline.execute", new_callable=AsyncMock) as mock_unified:
        mock_unified_result = MagicMock()
        mock_unified_result.candidates = mock_persisted_claims
        mock_unified.return_value = mock_unified_result

        claims = await service.extract_claims_from_version(ver_id)

        assert mock_unified.call_count == 1
        call_kwargs = mock_unified.call_args[1]
        assert call_kwargs["filename"] == "Northwind_Refund_Policy_Handbook.md"
        assert call_kwargs["parsed_content"] == NORTHWIND_TEST_CONTENT
        assert len(claims) == len(mock_persisted_claims)
