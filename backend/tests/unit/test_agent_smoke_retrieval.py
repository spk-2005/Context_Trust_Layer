"""
Unit Smoke Test: Agent Retrieval Boundary Verification for DOC-057.

Verifies that downstream agents consuming context via ContextRetrievalEngine
strictly retrieve certified v3 canonical atomic rules, and cannot retrieve:
1. Claim #54: Bad subject "the following"
2. Claim #63: Page-header leakage ("Page 8 of 11 Modifications to this Agreement Microsoft")
3. Claim #77: Address-subject leakage ("6880 Sierra Center Parkway Reno, Nevada")
4. Claim #96 / #83: False conflict introductory modifier ("Without limiting other remedies it")
5. Claim #71 / #72: Redundant duplicate assignment notices
6. Claim #4: Cross-reference text ("More details about cancelation can be found in the Product Terms")
"""

import decimal
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest


def build_doc57_sample_claim_set(org_id: uuid.UUID, ver_id: uuid.UUID) -> list[Claim]:
    """Builds test claim set containing canonical rules alongside known defective candidates."""
    doc = Document(id=uuid.uuid4(), organization_id=org_id, title="Microsoft Customer Agreement")
    ver = DocumentVersion(id=ver_id, document_id=doc.id, version_number=1, is_current=True)

    # 1. Canonical Atomic Rule: Product License Grant
    c_canon_license = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Microsoft grants Customer a nonexclusive, limited license to use Products ordered as provided in this Agreement.",
        subject="Microsoft",
        predicate="grants_product_license",
        object="a nonexclusive, limited license to Customer",
        claim_type="rule",
        status=ClaimStatus.VERIFIED,
    )
    c_canon_license.trust_scores = [ClaimTrustScore(claim_id=c_canon_license.id, overall_score=decimal.Decimal("0.9900"))]
    c_canon_license.validity_records = [ClaimValidity(claim_id=c_canon_license.id, is_current=True)]
    c_canon_license.evidence = [ClaimEvidence(claim_id=c_canon_license.id, document_id=doc.id, text_span="Microsoft grants Customer a nonexclusive and limited license", page_number=1)]

    # 2. Canonical Atomic Rule: Assignment Entitlement
    c_canon_assign = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Either party may assign this Agreement to an Affiliate.",
        subject="Each party",
        predicate="may_assign_to_affiliate",
        object="this Agreement to an Affiliate",
        claim_type="rule",
        status=ClaimStatus.VERIFIED,
    )
    c_canon_assign.trust_scores = [ClaimTrustScore(claim_id=c_canon_assign.id, overall_score=decimal.Decimal("0.9800"))]
    c_canon_assign.validity_records = [ClaimValidity(claim_id=c_canon_assign.id, is_current=True)]
    c_canon_assign.evidence = [ClaimEvidence(claim_id=c_canon_assign.id, document_id=doc.id, text_span="Either party may assign this Agreement to an Affiliate", page_number=8)]

    # 3. Defect #54: Bad Subject "the following"
    c_defect_54 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Upon such termination, the following will apply:",
        subject="the following",
        predicate="has_validity_rule",
        object="apply",
        claim_type="fragment",
        status=ClaimStatus.REJECTED,
    )
    c_defect_54.trust_scores = [ClaimTrustScore(claim_id=c_defect_54.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_54.validity_records = [ClaimValidity(claim_id=c_defect_54.id, is_current=True)]
    c_defect_54.evidence = [ClaimEvidence(claim_id=c_defect_54.id, document_id=doc.id, text_span="the following will apply", page_number=7)]

    # 4. Defect #63: Page Header Leakage
    c_defect_63 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Page 8 of 11 Modifications to this Agreement Microsoft may update this Agreement from time to time.",
        subject="Microsoft",
        predicate="update",
        object="this Agreement from time to time",
        claim_type="fragment",
        status=ClaimStatus.REJECTED,
    )
    c_defect_63.trust_scores = [ClaimTrustScore(claim_id=c_defect_63.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_63.validity_records = [ClaimValidity(claim_id=c_defect_63.id, is_current=True)]
    c_defect_63.evidence = [ClaimEvidence(claim_id=c_defect_63.id, document_id=doc.id, text_span="Page 8 of 11 Modifications", page_number=8)]

    # 5. Defect #77: Address Leakage
    c_defect_77 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="6880 Sierra Center Parkway Reno, Nevada 89511-1137 USA Microsoft may provide electronic notice.",
        subject="Microsoft",
        predicate="may_provide_electronic_notice",
        object="electronic notice",
        claim_type="fragment",
        status=ClaimStatus.REJECTED,
    )
    c_defect_77.trust_scores = [ClaimTrustScore(claim_id=c_defect_77.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_77.validity_records = [ClaimValidity(claim_id=c_defect_77.id, is_current=True)]
    c_defect_77.evidence = [ClaimEvidence(claim_id=c_defect_77.id, document_id=doc.id, text_span="6880 Sierra Center Parkway Reno, Nevada", page_number=9)]

    # 6. Defect #96 / #83: False Conflict / Introductory Modifier
    c_defect_96 = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Without limiting other remedies it may have, either party may terminate this Agreement on 30 days notice.",
        subject="Without limiting other remedies it",
        predicate="has_validity_rule",
        object="either party may terminate this Agreement on 30 days notice",
        claim_type="fragment",
        status=ClaimStatus.REJECTED,
    )
    c_defect_96.trust_scores = [ClaimTrustScore(claim_id=c_defect_96.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_96.validity_records = [ClaimValidity(claim_id=c_defect_96.id, is_current=True)]
    c_defect_96.evidence = [ClaimEvidence(claim_id=c_defect_96.id, document_id=doc.id, text_span="Without limiting other remedies it may have", page_number=7)]

    # 7. Defect #71/#72: Duplicate Assignment Notice
    c_defect_duplicate = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="Parties notify the other party in writing of the assignment.",
        subject="Each party",
        predicate="notify",
        object="other party in writing of the assignment",
        claim_type="duplicate",
        status=ClaimStatus.REJECTED,
    )
    c_defect_duplicate.trust_scores = [ClaimTrustScore(claim_id=c_defect_duplicate.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_duplicate.validity_records = [ClaimValidity(claim_id=c_defect_duplicate.id, is_current=True)]
    c_defect_duplicate.evidence = [ClaimEvidence(claim_id=c_defect_duplicate.id, document_id=doc.id, text_span="notify the other party in writing", page_number=8)]

    # 8. Defect #4: Cross-reference treated as policy rule
    c_defect_ref = Claim(
        id=uuid.uuid4(),
        organization_id=org_id,
        document_version_id=ver_id,
        claim_text="More details about cancelation can be found in the Product Terms.",
        subject="Customer",
        predicate="has_cancellation_fee_policy",
        object="details about cancelation in Product Terms",
        claim_type="reference",
        status=ClaimStatus.CANDIDATE,
    )
    c_defect_ref.trust_scores = [ClaimTrustScore(claim_id=c_defect_ref.id, overall_score=decimal.Decimal("0.5000"))]
    c_defect_ref.validity_records = [ClaimValidity(claim_id=c_defect_ref.id, is_current=True)]
    c_defect_ref.evidence = [ClaimEvidence(claim_id=c_defect_ref.id, document_id=doc.id, text_span="More details about cancelation can be found in the Product Terms", page_number=4)]

    return [
        c_canon_license,
        c_canon_assign,
        c_defect_54,
        c_defect_63,
        c_defect_77,
        c_defect_96,
        c_defect_duplicate,
        c_defect_ref,
    ]


@pytest.mark.asyncio
async def test_agent_smoke_retrieval_blocks_defects():
    """
    Smoke test: Verifies that ContextRetrievalEngine blocks all 6 defects:
    #54 'the following', #63 page-header, #77 address, #96 false conflict,
    #71/#72 duplicates, and #4 reference text.
    """
    org_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    all_claims = build_doc57_sample_claim_set(org_id, ver_id)

    # Setup mock async session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    # SQL query filtered to ACTIVE/VERIFIED rules
    # ContextRetrievalEngine filter ensures candidates/rejected are not returned
    valid_claims = [c for c in all_claims if c.status in [ClaimStatus.ACTIVE, ClaimStatus.VERIFIED] and c.claim_type == "rule"]
    mock_result.scalars.return_value.all.return_value = all_claims  # pass all claims to test in-memory hard gate
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    engine = ContextRetrievalEngine(mock_session)

    # 1. Query: "license grant terms"
    req_license = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="Microsoft product license grant",
        min_trust_score=decimal.Decimal("0.80"),
        canonical_only=True,
    )
    resp_license = await engine.query_context(req_license)

    # Verify #54 "the following" is NOT retrieved
    retrieved_texts = [item.claim.lower() for item in resp_license.context]
    retrieved_sources = [str(item.source.document) for item in resp_license.context]
    for text_val in retrieved_texts:
        assert "the following" not in text_val, "Defect #54 ('the following') must NOT be retrieved"
        assert "page 8 of 11" not in text_val, "Defect #63 (page-header) must NOT be retrieved"
        assert "sierra center parkway" not in text_val, "Defect #77 (address) must NOT be retrieved"
        assert "without limiting other remedies" not in text_val, "Defect #96 (false conflict) must NOT be retrieved"
        assert "more details about cancelation" not in text_val, "Defect #4 (reference text) must NOT be retrieved"

    assert len(resp_license.context) >= 1, "Canonical license claim must be retrieved"
    assert resp_license.context[0].is_canonical is True

    # 2. Query targeting assignment & notice: "assign agreement affiliate notice"
    req_assign = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="assign agreement affiliate notice",
        min_trust_score=decimal.Decimal("0.80"),
        canonical_only=True,
    )
    resp_assign = await engine.query_context(req_assign)

    assign_texts = [item.claim.lower() for item in resp_assign.context]
    # Check that canonical assignment is retrieved, but duplicate notice is NOT
    assert any("assign this agreement to an affiliate" in t for t in assign_texts), "Canonical assignment rule must be retrieved"
    assert not any("parties notify the other party in writing of the assignment" in t for t in assign_texts), "Duplicate notice claim #71/#72 must NOT be retrieved"


@pytest.mark.asyncio
async def test_agent_smoke_retrieval_direct_defect_queries():
    """
    Smoke test: Queries crafted specifically to evoke defective claims
    must refuse to return them.
    """
    org_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    all_claims = build_doc57_sample_claim_set(org_id, ver_id)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = all_claims
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    engine = ContextRetrievalEngine(mock_session)

    # Test #54 directly
    req_54 = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="upon such termination the following will apply",
        min_trust_score=decimal.Decimal("0.50"),
        canonical_only=True,
    )
    resp_54 = await engine.query_context(req_54)
    assert not any("the following" in item.claim.lower() for item in resp_54.context), "Claim #54 must be blocked"

    # Test #63 directly
    req_63 = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="Page 8 of 11 Modifications update agreement time to time",
        min_trust_score=decimal.Decimal("0.50"),
        canonical_only=True,
    )
    resp_63 = await engine.query_context(req_63)
    assert not any("page 8" in item.claim.lower() for item in resp_63.context), "Claim #63 must be blocked"

    # Test #77 directly
    req_77 = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="Reno Nevada Sierra Center Parkway notice",
        min_trust_score=decimal.Decimal("0.50"),
        canonical_only=True,
    )
    resp_77 = await engine.query_context(req_77)
    assert not any("reno" in item.claim.lower() for item in resp_77.context), "Claim #77 must be blocked"

    # Test #96 directly
    req_96 = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="without limiting other remedies terminate agreement 30 days",
        min_trust_score=decimal.Decimal("0.50"),
        canonical_only=True,
    )
    resp_96 = await engine.query_context(req_96)
    assert not any("without limiting other remedies" in item.claim.lower() for item in resp_96.context), "Claim #96 must be blocked"

    # Test #4 directly
    req_4 = ContextQueryRequest(
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        query="cancelation details in product terms site",
        min_trust_score=decimal.Decimal("0.50"),
        canonical_only=True,
    )
    resp_4 = await engine.query_context(req_4)
    assert not any("product terms" in item.claim.lower() for item in resp_4.context), "Claim #4 reference must be blocked"
