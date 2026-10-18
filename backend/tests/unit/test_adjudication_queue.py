"""
Unit tests for Blinded Independent Dual-Human Adjudication Queue.

Verifies strict governance enforcement:
1. Zero automated reviewer IDs allowed.
2. Independent Reviewer A & Reviewer B required.
3. Blinded review masks Reviewer A's disposition from Reviewer B.
4. Disagreements automatically escalate to third-party Adjudicator.
5. Certification fails closed on unreviewed, single-reviewed, or disputed items.
"""

from pathlib import Path
import pytest

from research.evaluation.adjudication_taxonomy import AdjudicationDisposition
from research.adjudication_queue.models import QueueItemStatus, AgreementStatus
from research.adjudication_queue.queue_manager import AdjudicationQueueManager


@pytest.fixture
def temp_queue(tmp_path: Path):
    queue_file = tmp_path / "test_pending_claims.json"
    return AdjudicationQueueManager(queue_path=queue_file)


@pytest.mark.fast
@pytest.mark.unit
def test_enqueue_initializes_pending_review_a(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-005",
        claim_id="cand-12345",
        claim_text="Vendor shall indemnify Tarion",
        subject="Vendor",
        predicate="has_indemnification_obligation",
        object_val="indemnify Tarion",
        evidence_span="Vendor shall indemnify Tarion",
        trigger_reason="Novel covenant terminology",
        composite_trust_score=0.82,
    )
    assert qid.startswith("QUEUE-DOC-005-")
    items = temp_queue.list_items("DOC-005")
    assert len(items) == 1
    assert items[0]["status"] == QueueItemStatus.PENDING_REVIEW_A.value
    assert items[0]["reviewer_a"] is None
    assert items[0]["reviewer_b"] is None


@pytest.mark.fast
@pytest.mark.unit
def test_forbidden_automated_reviewer_rejected(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-005",
        claim_id="cand-123",
        claim_text="Text",
        subject="S",
        predicate="P",
        object_val="O",
        evidence_span="Span",
        trigger_reason="Reason",
    )
    with pytest.raises(ValueError, match="forbidden: dual review requires independent human annotators"):
        temp_queue.submit_review(
            queue_id=qid,
            reviewer_id="Automated Rule Matcher",
            disposition=AdjudicationDisposition.GOLD_LABEL_GAP,
            rationale="Automated check",
        )


@pytest.mark.fast
@pytest.mark.unit
def test_reviewer_b_must_be_distinct_human(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-005",
        claim_id="cand-456",
        claim_text="Text",
        subject="S",
        predicate="P",
        object_val="O",
        evidence_span="Span",
        trigger_reason="Reason",
    )
    # Reviewer A submits
    temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="annotator_alice@enterprise.local",
        disposition=AdjudicationDisposition.GOLD_LABEL_GAP,
        rationale="Clear covenant omitted from gold",
    )
    # Same reviewer attempts Reviewer B
    with pytest.raises(ValueError, match="Reviewer B must be distinct from Reviewer A"):
        temp_queue.submit_review(
            queue_id=qid,
            reviewer_id="annotator_alice@enterprise.local",
            disposition=AdjudicationDisposition.GOLD_LABEL_GAP,
            rationale="Duplicate review attempt",
        )


@pytest.mark.fast
@pytest.mark.unit
def test_blinded_review_agreement_flow(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-009",
        claim_id="cand-789",
        claim_text="Return window 30 days",
        subject="Return window",
        predicate="has_duration",
        object_val="30 days",
        evidence_span="Return window 30 days",
        trigger_reason="Sub-threshold score",
    )
    # Alice reviews
    item = temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="alice@firm.org",
        disposition=AdjudicationDisposition.GOLD_LABEL_GAP,
        rationale="Missing from initial benchmark gold labels",
    )
    assert item.status == QueueItemStatus.PENDING_REVIEW_B

    # Bob reviews independently and agrees
    item = temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="bob@firm.org",
        disposition=AdjudicationDisposition.GOLD_LABEL_GAP,
        rationale="Concur: valid policy rule omitted from labels",
    )
    assert item.status == QueueItemStatus.READY_FOR_CERTIFICATION
    assert item.agreement == AgreementStatus.AGREED

    # Certify promotion by governance officer
    cert_record = temp_queue.certify_item(
        queue_id=qid,
        certifying_officer_id="charlie_officer@firm.org",
        merge_to_certified=False,
    )
    assert cert_record["disposition"] == AdjudicationDisposition.GOLD_LABEL_GAP.value
    assert cert_record["reviewer_1"] == "alice@firm.org"
    assert cert_record["reviewer_2"] == "bob@firm.org"
    assert cert_record["governance_certification"]["certifying_officer"] == "charlie_officer@firm.org"


@pytest.mark.fast
@pytest.mark.unit
def test_disagreement_and_third_party_adjudicator(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-009",
        claim_id="cand-dispute",
        claim_text="Return window ambiguous text",
        subject="Return window",
        predicate="has_duration",
        object_val="ambiguous",
        evidence_span="ambiguous",
        trigger_reason="Low confidence",
    )
    # Alice: CORRECT_FULL_MATCH
    temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="alice@firm.org",
        disposition=AdjudicationDisposition.CORRECT_FULL_MATCH,
        rationale="Valid full match",
    )
    # Bob: INCORRECT
    item = temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="bob@firm.org",
        disposition=AdjudicationDisposition.INCORRECT,
        rationale="Malformed span",
    )
    assert item.status == QueueItemStatus.ESCALATED_TO_ADJUDICATOR
    assert item.agreement == AgreementStatus.DISAGREED

    # Single-reviewer certification attempt must fail closed
    with pytest.raises(ValueError, match="Governance Barrier Knockout"):
        temp_queue.certify_item(queue_id=qid, certifying_officer_id="lead@firm.org", merge_to_certified=False)

    # Alice or Bob cannot be Adjudicator
    with pytest.raises(ValueError, match="Adjudicator cannot be Reviewer A"):
        temp_queue.resolve_disagreement(
            queue_id=qid,
            adjudicator_id="alice@firm.org",
            final_disposition=AdjudicationDisposition.ACCEPTED_PARTIAL_MATCH,
            rationale="Self-adjudication attempt",
        )

    # Third independent human adjudicates
    item = temp_queue.resolve_disagreement(
        queue_id=qid,
        adjudicator_id="clara_specialist@firm.org",
        final_disposition=AdjudicationDisposition.ACCEPTED_PARTIAL_MATCH,
        rationale="Span captures object partially; accept as partial match",
    )
    assert item.status == QueueItemStatus.READY_FOR_CERTIFICATION

    # Now certification succeeds
    cert = temp_queue.certify_item(
        queue_id=qid,
        certifying_officer_id="lead@firm.org",
        merge_to_certified=False,
    )
    assert cert["disposition"] == AdjudicationDisposition.ACCEPTED_PARTIAL_MATCH.value
    assert cert["governance_certification"]["escalated_to_adjudicator"] is True


@pytest.mark.fast
@pytest.mark.unit
def test_blinded_listing_masks_reviewer_a(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-001",
        claim_id="cand-blind",
        claim_text="Text",
        subject="S",
        predicate="P",
        object_val="O",
        evidence_span="Span",
        trigger_reason="Reason",
    )
    temp_queue.submit_review(
        queue_id=qid,
        reviewer_id="alice@firm.org",
        disposition=AdjudicationDisposition.NON_CANONICAL,
        rationale="Proprietary reasoning that would bias reviewer B",
    )

    # Listed for Alice: visible
    alice_view = temp_queue.list_items("DOC-001", blinded_for_reviewer="alice@firm.org")
    assert alice_view[0]["reviewer_a"]["disposition"] == AdjudicationDisposition.NON_CANONICAL.value

    # Listed for Bob: BLINDED
    bob_view = temp_queue.list_items("DOC-001", blinded_for_reviewer="bob@firm.org")
    assert bob_view[0]["reviewer_a"]["disposition"] == "[BLINDED]"
    assert bob_view[0]["reviewer_a"]["rationale"] == "[BLINDED]"