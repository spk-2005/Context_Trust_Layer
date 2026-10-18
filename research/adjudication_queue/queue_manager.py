"""
Asynchronous Blinded Dual-Human Adjudication Queue Manager.

Enforces rigorous independent dual-human review standards:
1. Reviewer A evaluates candidate claim in isolation.
2. Reviewer B evaluates candidate claim blinded to Reviewer A's disposition.
3. System validates consensus:
   - If agreed: advances to READY_FOR_CERTIFICATION.
   - If disagreed: escalates to a designated third human Adjudicator.
4. Independent Certification Gate:
   - Items are never auto-certified or certified by a single reviewer.
   - Explicit authorized officer action is required to promote to certified adjudications.json.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from research.evaluation.adjudication_taxonomy import AdjudicationDisposition
from research.adjudication_queue.models import (
    AgreementStatus,
    DualReviewQueueItem,
    QueueItemStatus,
    ReviewerAssessment,
    AdjudicatorAssessment,
)

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_PATH = Path("B:/Context_Layer_Ai/research/adjudication_queue/pending_claims.json")
CERTIFIED_ADJUDICATIONS_PATH = Path("B:/Context_Layer_Ai/research/evaluation/adjudications.json")

FORBIDDEN_REVIEWER_IDS = {
    "automated rule matcher",
    "system",
    "bot",
    "automated_matcher",
    "auto",
}


class AdjudicationQueueManager:
    """Manages independent dual-human adjudication queue."""

    def __init__(self, queue_path: Optional[Path] = None):
        self.queue_path = queue_path or DEFAULT_QUEUE_PATH
        if not self.queue_path.exists():
            self.queue_path.parent.mkdir(parents=True, exist_ok=True)
            self.queue_path.write_text("[]", encoding="utf-8")

    def _load_queue(self) -> List[DualReviewQueueItem]:
        try:
            raw = json.loads(self.queue_path.read_text(encoding="utf-8"))
            return [DualReviewQueueItem.model_validate(item) for item in raw]
        except Exception as e:
            logger.warning("Error loading adjudication queue: %s", e)
            return []

    def _save_queue(self, items: List[DualReviewQueueItem]) -> None:
        payload = [item.model_dump(mode="json") for item in items]
        self.queue_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enqueue_candidate(
        self,
        document_id: str,
        claim_id: str,
        claim_text: str,
        subject: str,
        predicate: str,
        object_val: str,
        evidence_span: str,
        trigger_reason: str,
        composite_trust_score: float = 0.0,
        locator: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Enqueues candidate claim for asynchronous dual-human review. Idempotent by (document_id, claim_id)."""
        items = self._load_queue()

        existing = next((i for i in items if i.claim_id == claim_id and i.document_id == document_id), None)
        if existing:
            return existing.queue_id

        queue_id = f"QUEUE-{document_id}-{uuid.uuid4().hex[:8]}"
        item = DualReviewQueueItem(
            queue_id=queue_id,
            document_id=document_id,
            claim_id=claim_id,
            claim_text=claim_text,
            subject=subject,
            predicate=predicate,
            object=object_val,
            evidence_span=evidence_span,
            locator=locator or {},
            trigger_reason=trigger_reason,
            composite_trust_score=composite_trust_score,
            status=QueueItemStatus.PENDING_REVIEW_A,
        )
        items.append(item)
        self._save_queue(items)
        return queue_id

    def submit_review(
        self,
        queue_id: str,
        reviewer_id: str,
        disposition: str | AdjudicationDisposition,
        rationale: str,
        component_scores: Optional[Dict[str, float]] = None,
    ) -> DualReviewQueueItem:
        """Submits independent review for Reviewer A or Reviewer B."""
        clean_reviewer = reviewer_id.strip()
        if clean_reviewer.lower() in FORBIDDEN_REVIEWER_IDS:
            raise ValueError(f"Reviewer ID '{reviewer_id}' is forbidden: dual review requires independent human annotators.")

        if isinstance(disposition, str):
            disposition = AdjudicationDisposition(disposition)

        items = self._load_queue()
        target = next((i for i in items if i.queue_id == queue_id), None)
        if not target:
            raise KeyError(f"Queue item {queue_id} not found.")

        assessment = ReviewerAssessment(
            reviewer_id=clean_reviewer,
            disposition=disposition,
            rationale=rationale,
            component_scores=component_scores or {
                "subject": 1.0,
                "predicate": 1.0,
                "object": 1.0,
                "modality": 1.0,
                "evidence": 1.0,
            },
        )

        # Slot 1: Reviewer A
        if target.reviewer_a is None:
            target.reviewer_a = assessment
            target.status = QueueItemStatus.PENDING_REVIEW_B

        # Slot 2: Reviewer B (Must be a different independent human)
        elif target.reviewer_b is None:
            if clean_reviewer == target.reviewer_a.reviewer_id:
                raise ValueError("Reviewer B must be distinct from Reviewer A for independent dual-human adjudication.")

            target.reviewer_b = assessment

            # Consensus check
            if target.reviewer_a.disposition == target.reviewer_b.disposition:
                target.agreement = AgreementStatus.AGREED
                target.status = QueueItemStatus.READY_FOR_CERTIFICATION
            else:
                target.agreement = AgreementStatus.DISAGREED
                target.status = QueueItemStatus.ESCALATED_TO_ADJUDICATOR

        else:
            raise ValueError(f"Queue item {queue_id} already has both Reviewer A and Reviewer B recorded.")

        self._save_queue(items)
        return target

    def resolve_disagreement(
        self,
        queue_id: str,
        adjudicator_id: str,
        final_disposition: str | AdjudicationDisposition,
        rationale: str,
    ) -> DualReviewQueueItem:
        """Adjudicates item when Reviewer A and Reviewer B disagreed."""
        clean_adjudicator = adjudicator_id.strip()
        if clean_adjudicator.lower() in FORBIDDEN_REVIEWER_IDS:
            raise ValueError("Adjudicator must be an authorized human specialist.")

        if isinstance(final_disposition, str):
            final_disposition = AdjudicationDisposition(final_disposition)

        items = self._load_queue()
        target = next((i for i in items if i.queue_id == queue_id), None)
        if not target:
            raise KeyError(f"Queue item {queue_id} not found.")

        if target.status != QueueItemStatus.ESCALATED_TO_ADJUDICATOR:
            raise ValueError(f"Cannot adjudicate item in status {target.status.value}; must be ESCALATED_TO_ADJUDICATOR.")

        if target.reviewer_a and clean_adjudicator == target.reviewer_a.reviewer_id:
            raise ValueError("Adjudicator cannot be Reviewer A.")
        if target.reviewer_b and clean_adjudicator == target.reviewer_b.reviewer_id:
            raise ValueError("Adjudicator cannot be Reviewer B.")

        target.adjudicator = AdjudicatorAssessment(
            adjudicator_id=clean_adjudicator,
            final_disposition=final_disposition,
            rationale=rationale,
        )
        target.status = QueueItemStatus.READY_FOR_CERTIFICATION
        self._save_queue(items)
        return target

    def certify_item(
        self,
        queue_id: str,
        certifying_officer_id: str,
        merge_to_certified: bool = True,
    ) -> Dict[str, Any]:
        """Promotes a fully validated dual-reviewed item into certified adjudications."""
        clean_officer = certifying_officer_id.strip()
        if clean_officer.lower() in FORBIDDEN_REVIEWER_IDS:
            raise ValueError("Certifying officer must be an authorized compliance lead.")

        items = self._load_queue()
        target = next((i for i in items if i.queue_id == queue_id), None)
        if not target:
            raise KeyError(f"Queue item {queue_id} not found.")

        if target.status != QueueItemStatus.READY_FOR_CERTIFICATION:
            raise ValueError(
                f"Governance Barrier Knockout: Cannot certify item {queue_id} in status '{target.status.value}'. "
                "Must be 'READY_FOR_CERTIFICATION' with verified dual-human consensus or adjudicator resolution."
            )

        if not target.reviewer_a or not target.reviewer_b:
            raise ValueError("Governance Barrier Knockout: Both Reviewer A and Reviewer B assessments are required.")

        # Determine certified disposition
        if target.adjudicator:
            effective_disposition = target.adjudicator.final_disposition
            effective_rationale = (
                f"[Adjudicated by {target.adjudicator.adjudicator_id}]: {target.adjudicator.rationale} "
                f"(Reviewer A ({target.reviewer_a.reviewer_id}): {target.reviewer_a.disposition.value}; "
                f"Reviewer B ({target.reviewer_b.reviewer_id}): {target.reviewer_b.disposition.value})"
            )
        else:
            effective_disposition = target.reviewer_a.disposition
            effective_rationale = (
                f"[Dual-Review Consensus]: Reviewer A ({target.reviewer_a.reviewer_id}) & "
                f"Reviewer B ({target.reviewer_b.reviewer_id}) agreed. {target.reviewer_a.rationale}"
            )

        adj_id = f"ADJ-{target.document_id}-{target.claim_id[:8]}"
        cert_record = {
            "adjudication_id": adj_id,
            "document_id": target.document_id,
            "claim_id": target.claim_id,
            "gold_claim_id_or_null": effective_disposition.value,
            "reviewer_1": target.reviewer_a.reviewer_id,
            "reviewer_2": target.reviewer_b.reviewer_id,
            "adjudicator_consensus": effective_disposition.value,
            "disposition": effective_disposition.value,
            "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "component_scores": target.reviewer_a.component_scores,
            "evidence_span": target.evidence_span,
            "rationale": effective_rationale,
            "governance_certification": {
                "certifying_officer": clean_officer,
                "certified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "agreement": target.agreement.value if target.agreement else None,
                "escalated_to_adjudicator": bool(target.adjudicator),
            },
        }

        target.status = QueueItemStatus.CERTIFIED
        target.certification_officer_id = clean_officer
        target.certified_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target.certified_adjudication_id = adj_id
        self._save_queue(items)

        if merge_to_certified and CERTIFIED_ADJUDICATIONS_PATH.exists():
            try:
                cert_list = json.loads(CERTIFIED_ADJUDICATIONS_PATH.read_text(encoding="utf-8"))
                # Replace existing if present or append
                cert_list = [c for c in cert_list if c.get("adjudication_id") != adj_id]
                cert_list.append(cert_record)
                CERTIFIED_ADJUDICATIONS_PATH.write_text(json.dumps(cert_list, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error("Failed to append to certified adjudications.json: %s", e)

        return cert_record

    def list_items(
        self,
        document_id: Optional[str] = None,
        status: Optional[QueueItemStatus] = None,
        blinded_for_reviewer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists items in queue. When blinded_for_reviewer is set, masks Reviewer A details from Reviewer B."""
        items = self._load_queue()
        filtered = [
            i for i in items
            if (document_id is None or i.document_id == document_id)
            and (status is None or i.status == status)
        ]

        out: List[Dict[str, Any]] = []
        for item in filtered:
            data = item.model_dump(mode="json")
            if blinded_for_reviewer and item.reviewer_a and blinded_for_reviewer != item.reviewer_a.reviewer_id:
                # Blind Reviewer B from Reviewer A's decisions
                data["reviewer_a"] = {
                    "reviewer_id": "[BLINDED]",
                    "disposition": "[BLINDED]",
                    "rationale": "[BLINDED]",
                }
            out.append(data)
        return out

    def get_stats(self) -> Dict[str, Any]:
        """Returns detailed queue status counts."""
        items = self._load_queue()
        counts: Dict[str, int] = {s.value: 0 for s in QueueItemStatus}
        for item in items:
            counts[item.status.value] = counts.get(item.status.value, 0) + 1

        return {
            "total_items": len(items),
            "pending_review_a": counts[QueueItemStatus.PENDING_REVIEW_A.value],
            "pending_review_b": counts[QueueItemStatus.PENDING_REVIEW_B.value],
            "ready_for_certification": counts[QueueItemStatus.READY_FOR_CERTIFICATION.value],
            "escalated_to_adjudicator": counts[QueueItemStatus.ESCALATED_TO_ADJUDICATOR.value],
            "certified": counts[QueueItemStatus.CERTIFIED.value],
            "rejected": counts[QueueItemStatus.REJECTED.value],
        }