"""
Unit tests for Asynchronous Adjudication Queue.
"""

from pathlib import Path
import pytest

from research.adjudication_queue.queue_manager import AdjudicationQueueManager


@pytest.fixture
def temp_queue(tmp_path: Path):
    queue_file = tmp_path / "test_pending_claims.json"
    return AdjudicationQueueManager(queue_path=queue_file)


@pytest.mark.fast
@pytest.mark.unit
def test_enqueue_and_list_pending(temp_queue: AdjudicationQueueManager):
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

    pending = temp_queue.list_pending("DOC-005")
    assert len(pending) == 1
    assert pending[0]["claim_id"] == "cand-12345"
    assert pending[0]["status"] == "PENDING"

    # Idempotent enqueue
    qid2 = temp_queue.enqueue_candidate(
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
    assert qid == qid2
    assert len(temp_queue.list_pending("DOC-005")) == 1


@pytest.mark.fast
@pytest.mark.unit
def test_adjudicate_queue_item(temp_queue: AdjudicationQueueManager):
    qid = temp_queue.enqueue_candidate(
        document_id="DOC-009",
        claim_id="cand-99999",
        claim_text="Return window 30 days",
        subject="Return window",
        predicate="has_duration",
        object_val="30 days",
        evidence_span="Return window 30 days",
        trigger_reason="Sub-threshold score",
    )

    record = temp_queue.adjudicate_item(
        queue_id=qid,
        disposition="GOLD_LABEL_GAP",
        rationale="Valid return window omitted from benchmark labels",
        reviewer="Test Reviewer",
    )
    assert record is not None
    assert record["disposition"] == "GOLD_LABEL_GAP"
    assert record["reviewer_2"] == "Test Reviewer"

    # No longer pending
    assert len(temp_queue.list_pending("DOC-009")) == 0
    stats = temp_queue.get_stats()
    assert stats["total_items"] == 1
    assert stats["pending_count"] == 0
    assert stats["adjudicated_count"] == 1