import decimal
import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.repositories.claim_repository import ClaimRepository
from app.extraction.subject_normalizer import EntityType, SubjectNormalizer
from app.api.v1.review import ClaimReviewActionRequest, execute_claim_review_action


# =========================================================================
# 1. Subject Entity Classification & Typing
# =========================================================================

def test_subject_normalizer_entity_typing():
    """
    Verifies that SubjectNormalizer classifies normalized entities into
    controlled enterprise EntityType categories.
    """
    # Customer Tiers
    assert SubjectNormalizer.classify_entity_type("Northwind Rewards Gold members") == EntityType.CUSTOMER_TIER.value
    assert SubjectNormalizer.classify_entity_type("Business customer with standard account") == EntityType.CUSTOMER_TIER.value
    assert SubjectNormalizer.classify_entity_type("VIP account holder") == EntityType.CUSTOMER_TIER.value

    # Payment Methods
    assert SubjectNormalizer.classify_entity_type("Debit card") == EntityType.PAYMENT_METHOD.value
    assert SubjectNormalizer.classify_entity_type("Store credit") == EntityType.PAYMENT_METHOD.value
    assert SubjectNormalizer.classify_entity_type("Bank transfer") == EntityType.PAYMENT_METHOD.value
    assert SubjectNormalizer.classify_entity_type("Cash") == EntityType.PAYMENT_METHOD.value

    # Order States
    assert SubjectNormalizer.classify_entity_type("Shipped order") == EntityType.ORDER_STATE.value
    assert SubjectNormalizer.classify_entity_type("Refund request") == EntityType.ORDER_STATE.value
    assert SubjectNormalizer.classify_entity_type("Order cancellation") == EntityType.ORDER_STATE.value

    # Process Stages
    assert SubjectNormalizer.classify_entity_type("Warehouse inspection") == EntityType.PROCESS_STAGE.value
    assert SubjectNormalizer.classify_entity_type("Warehouse transit") == EntityType.PROCESS_STAGE.value
    assert SubjectNormalizer.classify_entity_type("Bank transfer processing") == EntityType.PROCESS_STAGE.value
    assert SubjectNormalizer.classify_entity_type("Posting duration") == EntityType.PROCESS_STAGE.value

    # Authorization Tiers & Organizational Roles
    assert SubjectNormalizer.classify_entity_type("Refund approval") == EntityType.AUTHORIZATION_TIER.value
    assert SubjectNormalizer.classify_entity_type("Tier 2 Support Lead") == EntityType.AUTHORIZATION_TIER.value
    assert SubjectNormalizer.classify_entity_type("Finance Director") == EntityType.AUTHORIZATION_TIER.value

    # Product Scope (Default Fallback)
    assert SubjectNormalizer.classify_entity_type("Standard merchandise") == EntityType.PRODUCT_SCOPE.value
    assert SubjectNormalizer.classify_entity_type("Defective tent") == EntityType.PRODUCT_SCOPE.value
    assert SubjectNormalizer.classify_entity_type("Trailhead box") == EntityType.POLICY_DOMAIN.value


def test_subject_normalizer_normalize_to_object():
    """
    Verifies that normalize_to_object returns a strongly-typed SubjectObject
    with correct normalization status and entity classification.
    """
    # 1. Preamble fragment with unclosed parenthesis -> Customer tier
    obj1 = SubjectNormalizer.normalize_to_object("Business customers on standard accounts (custom contracts")
    assert obj1.entity == "Business customer with standard account"
    assert obj1.entity_type == EntityType.CUSTOMER_TIER.value
    assert obj1.normalized is True

    # 2. Conversational prefix with pricing -> Product scope
    obj2 = SubjectNormalizer.normalize_to_object("For damaged items valued under $40.00, we")
    assert obj2.entity == "Damaged item valued under $40"
    assert obj2.entity_type == EntityType.PRODUCT_SCOPE.value
    assert obj2.normalized is True

    # 3. Conversational preamble -> Order state
    obj3 = SubjectNormalizer.normalize_to_object("The order number or proof of purchase")
    assert obj3.entity == "Refund request"
    assert obj3.entity_type == EntityType.ORDER_STATE.value
    assert obj3.normalized is True

    # 4. Ungrounded pronoun fragment -> Fails normalization
    obj4 = SubjectNormalizer.normalize_to_object("We will then process the payment")
    assert obj4.normalized is False


# =========================================================================
# 2. Deterministic Claim Hash Computation
# =========================================================================

def test_deterministic_claim_hash_consistency():
    """
    Verifies that compute_claim_hash generates identical SHA-256 digests
    for identical parameters and changes deterministically when any field differs.
    """
    doc_id = "NW-POL-REF-2026"
    version = "4.2"
    subj = "Standard merchandise"
    pred = "has_return_window"
    val = 30
    conds = [{"field": "customer_tier", "value": "standard"}]

    hash_1 = ClaimRepository.compute_claim_hash(doc_id, version, subj, pred, val, conds)
    hash_2 = ClaimRepository.compute_claim_hash(doc_id, version, subj, pred, val, conds)
    assert hash_1 == hash_2
    assert len(hash_1) == 64  # SHA-256 hex length

    # Version change changes hash
    hash_v5 = ClaimRepository.compute_claim_hash(doc_id, "5.0", subj, pred, val, conds)
    assert hash_v5 != hash_1

    # Subject change changes hash
    hash_gold = ClaimRepository.compute_claim_hash(doc_id, version, "Gold members", pred, val, conds)
    assert hash_gold != hash_1


# =========================================================================
# 3. Document Versioning & Claim Superseding
# =========================================================================

@pytest.mark.asyncio
async def test_claim_superseding_on_version_update():
    """
    Verifies that ClaimRepository.supersede_claims_for_document identifies
    older claims from prior versions and marks them SUPERSEDED with validity revoked.
    """
    mock_session = AsyncMock()

    # Simulate query finding 2 older claim IDs
    old_claim_id_1 = uuid.uuid4()
    old_claim_id_2 = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.all.return_value = [(old_claim_id_1,), (old_claim_id_2,)]
    mock_session.execute.return_value = mock_result

    repo = ClaimRepository(mock_session)
    doc_id = uuid.uuid4()
    new_ver_id = uuid.uuid4()

    superseded_count = await repo.supersede_claims_for_document(doc_id, new_ver_id)
    assert superseded_count == 2
    assert mock_session.execute.call_count >= 2
    mock_session.flush.assert_awaited()


# =========================================================================
# 4. Review Workflow Triage Actions
# =========================================================================

@pytest.mark.asyncio
async def test_review_action_approve():
    """
    Verifies that approving a queued candidate claim marks it VERIFIED
    and sets human trust score to 1.0.
    """
    claim_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    claim = Claim(
        id=claim_id,
        organization_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        claim_text="Standard merchandise has a return window of 30 days.",
        subject="Standard merchandise",
        predicate="has_return_window",
        object="30 days",
        status=ClaimStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
    )
    score = ClaimTrustScore(
        id=uuid.uuid4(),
        claim_id=claim_id,
        source_score=decimal.Decimal("0.9"),
        freshness_score=decimal.Decimal("1.0"),
        evidence_score=decimal.Decimal("0.85"),
        consistency_score=decimal.Decimal("0.9"),
        authority_score=decimal.Decimal("1.0"),
        human_score=decimal.Decimal("0.5"),
        overall_score=decimal.Decimal("0.84"),
        calculated_at=now,
    )
    val = ClaimValidity(
        id=uuid.uuid4(),
        claim_id=claim_id,
        is_current=False,
        validity_status="unverified",
        created_at=now,
    )
    claim.trust_scores = [score]
    claim.validity_records = [val]

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = claim
    mock_db.execute.return_value = mock_res

    req = ClaimReviewActionRequest(action="approve", reviewer_notes="Confirmed by compliance")
    res = await execute_claim_review_action(claim_id, req, mock_db)

    assert claim.status == ClaimStatus.VERIFIED
    assert score.human_score == decimal.Decimal("1.0")
    assert val.is_current is True
    assert val.validity_status == "verified"
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_review_action_edit():
    """
    Verifies that editing a candidate claim updates attributes, promotes to VERIFIED,
    and sets human trust score to 1.0.
    """
    claim_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    claim = Claim(
        id=claim_id,
        organization_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        claim_text="Rough unedited fragment 30 days",
        subject="fragment",
        predicate="is",
        object="30 days",
        status=ClaimStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
    )
    score = ClaimTrustScore(
        id=uuid.uuid4(),
        claim_id=claim_id,
        source_score=decimal.Decimal("0.9"),
        freshness_score=decimal.Decimal("1.0"),
        evidence_score=decimal.Decimal("0.85"),
        consistency_score=decimal.Decimal("0.9"),
        authority_score=decimal.Decimal("1.0"),
        human_score=decimal.Decimal("0.5"),
        overall_score=decimal.Decimal("0.75"),
        calculated_at=now,
    )
    val = ClaimValidity(
        id=uuid.uuid4(),
        claim_id=claim_id,
        is_current=False,
        validity_status="unverified",
        created_at=now,
    )
    claim.trust_scores = [score]
    claim.validity_records = [val]

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = claim
    mock_db.execute.return_value = mock_res

    req = ClaimReviewActionRequest(
        action="edit",
        edited_claim_text="Standard merchandise has a return window of 30 days.",
        edited_subject="Standard merchandise",
        edited_predicate="has_return_window",
        edited_object="30 days",
    )
    res = await execute_claim_review_action(claim_id, req, mock_db)

    assert claim.subject == "Standard merchandise"
    assert claim.predicate == "has_return_window"
    assert claim.status == ClaimStatus.VERIFIED
    assert score.human_score == decimal.Decimal("1.0")
    assert val.is_current is True
