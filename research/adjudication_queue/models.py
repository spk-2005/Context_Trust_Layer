"""
Pydantic Models for Independent Dual-Human Adjudication Queue.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from research.evaluation.adjudication_taxonomy import AdjudicationDisposition


class QueueItemStatus(str, Enum):
    PENDING_REVIEW_A = "PENDING_REVIEW_A"
    PENDING_REVIEW_B = "PENDING_REVIEW_B"
    READY_FOR_CERTIFICATION = "READY_FOR_CERTIFICATION"
    ESCALATED_TO_ADJUDICATOR = "ESCALATED_TO_ADJUDICATOR"
    CERTIFIED = "CERTIFIED"
    REJECTED = "REJECTED"


class AgreementStatus(str, Enum):
    AGREED = "AGREED"
    DISAGREED = "DISAGREED"


class ReviewerAssessment(BaseModel):
    reviewer_id: str
    disposition: AdjudicationDisposition
    rationale: str
    reviewed_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    component_scores: Dict[str, float] = Field(
        default_factory=lambda: {
            "subject": 1.0,
            "predicate": 1.0,
            "object": 1.0,
            "modality": 1.0,
            "evidence": 1.0,
        }
    )


class AdjudicatorAssessment(BaseModel):
    adjudicator_id: str
    final_disposition: AdjudicationDisposition
    rationale: str
    adjudicated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class DualReviewQueueItem(BaseModel):
    queue_id: str
    document_id: str
    claim_id: str
    claim_text: str
    subject: str
    predicate: str
    object: str
    evidence_span: str
    locator: Dict[str, Any] = Field(default_factory=dict)
    trigger_reason: str
    composite_trust_score: float = 0.0
    status: QueueItemStatus = QueueItemStatus.PENDING_REVIEW_A
    enqueued_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    reviewer_a: Optional[ReviewerAssessment] = None
    reviewer_b: Optional[ReviewerAssessment] = None
    agreement: Optional[AgreementStatus] = None
    adjudicator: Optional[AdjudicatorAssessment] = None
    certification_officer_id: Optional[str] = None
    certified_at: Optional[str] = None
    certified_adjudication_id: Optional[str] = None