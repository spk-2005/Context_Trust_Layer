"""
Asynchronous Adjudication Queue Manager.

Decouples human review from developer workflows:
- Unjudged or sub-threshold claims from Layer 6 validation are enqueued asynchronously.
- Human annotators / compliance specialists review items independently of CI/pre-commit.
- Approved adjudications are merged into certified adjudications.json upon completion.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_PATH = Path("B:/Context_Layer_Ai/research/adjudication_queue/pending_claims.json")
CERTIFIED_ADJUDICATIONS_PATH = Path("B:/Context_Layer_Ai/research/evaluation/adjudications.json")


class AdjudicationQueueManager:
    """Manages asynchronous human adjudication queue."""

    def __init__(self, queue_path: Optional[Path] = None):
        self.queue_path = queue_path or DEFAULT_QUEUE_PATH
        if not self.queue_path.exists():
            self.queue_path.parent.mkdir(parents=True, exist_ok=True)
            self.queue_path.write_text("[]", encoding="utf-8")

    def _load_queue(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.queue_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Error loading adjudication queue: %s", e)
            return []

    def _save_queue(self, items: List[Dict[str, Any]]) -> None:
        self.queue_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")

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
        """Enqueues candidate claim for asynchronous human review. Idempotent by claim_id."""
        items = self._load_queue()

        # Check existing
        existing = next((i for i in items if i.get("claim_id") == claim_id and i.get("document_id") == document_id), None)
        if existing:
            return existing["queue_id"]

        queue_id = f"QUEUE-{document_id}-{uuid.uuid4().hex[:8]}"
        record = {
            "queue_id": queue_id,
            "document_id": document_id,
            "claim_id": claim_id,
            "claim_text": claim_text,
            "subject": subject,
            "predicate": predicate,
            "object": object_val,
            "evidence_span": evidence_span,
            "locator": locator or {},
            "trigger_reason": trigger_reason,
            "composite_trust_score": composite_trust_score,
            "status": "PENDING",
            "enqueued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "adjudication": None,
        }
        items.append(record)
        self._save_queue(items)
        return queue_id

    def list_pending(self, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists pending unreviewed claims."""
        items = self._load_queue()
        return [
            i for i in items
            if i.get("status") == "PENDING"
            and (document_id is None or i.get("document_id") == document_id)
        ]

    def adjudicate_item(
        self,
        queue_id: str,
        disposition: str,
        rationale: str,
        reviewer: str = "Compliance Specialist",
        component_scores: Optional[Dict[str, float]] = None,
        gold_claim_id: Optional[str] = None,
        merge_to_certified: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Adjudicates a pending queue item. Optionally merges into certified adjudications."""
        items = self._load_queue()
        target = next((i for i in items if i.get("queue_id") == queue_id), None)
        if not target:
            return None

        adj_id = f"ADJ-{target['document_id']}-{target['claim_id'][:8]}"
        adj_record = {
            "adjudication_id": adj_id,
            "document_id": target["document_id"],
            "claim_id": target["claim_id"],
            "gold_claim_id_or_null": gold_claim_id or disposition,
            "reviewer_1": "Automated Rule Matcher",
            "reviewer_2": reviewer,
            "adjudicator_consensus": disposition,
            "disposition": disposition,
            "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "component_scores": component_scores or {
                "subject": 1.0,
                "predicate": 1.0,
                "object": 1.0,
                "modality": 1.0,
                "evidence": 1.0,
            },
            "evidence_span": target["evidence_span"],
            "rationale": rationale,
        }

        target["status"] = "ADJUDICATED"
        target["adjudication"] = adj_record
        self._save_queue(items)

        if merge_to_certified and CERTIFIED_ADJUDICATIONS_PATH.exists():
            try:
                cert = json.loads(CERTIFIED_ADJUDICATIONS_PATH.read_text(encoding="utf-8"))
                cert.append(adj_record)
                CERTIFIED_ADJUDICATIONS_PATH.write_text(json.dumps(cert, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error("Failed to merge adjudication to certified file: %s", e)

        return adj_record

    def get_stats(self) -> Dict[str, Any]:
        """Returns queue statistics."""
        items = self._load_queue()
        total = len(items)
        pending = sum(1 for i in items if i.get("status") == "PENDING")
        adjudicated = sum(1 for i in items if i.get("status") == "ADJUDICATED")
        by_doc: Dict[str, int] = {}
        for i in items:
            d = i.get("document_id", "UNKNOWN")
            by_doc[d] = by_doc.get(d, 0) + 1
        return {
            "total_items": total,
            "pending_count": pending,
            "adjudicated_count": adjudicated,
            "by_document": by_doc,
        }