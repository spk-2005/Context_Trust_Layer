"""
Feedback Telemetry & Failure Taxonomy Service (Atlan Feedback Loop Pattern).

Enables rigorous diagnostic tracking of Copilot errors:
Instead of treating failures as generic "bad model responses", every issue
is classified into an actionable pipeline stage:
- PARSING: Document linearization or layout table error
- EXTRACTION: Meaning divergence (e.g. 'immediately upon receipt' became '30 days')
- REFERENCE_LABELS: Stale document version, wrong section tag
- RETRIEVAL: RRF search failed to surface the operative clause
- MISSING_CONTEXT: Legitimate policy gap (unanswerable topic)
- GENERATION: LLM hallucination or invented entity
- VERIFICATION: AnswerVerifier flagged ungrounded number or missing citation
- AUTHORIZATION: Scoped RBAC boundary violation
- UI_DISPLAY: Presentation or citation chip rendering issue
"""

import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FailureTaxonomyStage(str, enum.Enum):
    PARSING = "parsing"
    EXTRACTION = "extraction"
    REFERENCE_LABELS = "reference_labels"
    RETRIEVAL = "retrieval"
    MISSING_CONTEXT = "missing_context"
    GENERATION = "generation"
    VERIFICATION = "verification"
    AUTHORIZATION = "authorization"
    UI_DISPLAY = "ui_display"


class FeedbackSubmitRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str = Field(description="'thumbs_up', 'thumbs_down', or 'disputed'")
    failure_stage: FailureTaxonomyStage | None = None
    notes: str | None = None
    suggested_correction: str | None = None
    user_id: str | None = None
    user_role: str | None = None


# In-memory store for feedback telemetry (and can write to DB/ActivityLog)
_FEEDBACK_LOG: list[dict[str, Any]] = []


class FeedbackTelemetryService:
    """Service to record, categorize, and route Copilot failures to Data Stewards."""

    @classmethod
    def record_feedback(cls, request_in: FeedbackSubmitRequest) -> dict[str, Any]:
        """Records a user/evaluator feedback event with failure taxonomy."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "message_id": request_in.message_id,
            "session_id": request_in.session_id,
            "user_id": request_in.user_id,
            "user_role": request_in.user_role or "evaluator",
            "rating": request_in.rating,
            "failure_stage": request_in.failure_stage.value if request_in.failure_stage else None,
            "notes": request_in.notes,
            "suggested_correction": request_in.suggested_correction,
            "status": "staged_for_steward" if request_in.rating != "thumbs_up" else "closed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _FEEDBACK_LOG.append(record)
        logger.info(
            "Copilot feedback recorded: %s (Rating: %s, Stage: %s)",
            record_id,
            request_in.rating,
            request_in.failure_stage,
        )
        return record

    @classmethod
    def get_stage_distribution(cls) -> dict[str, Any]:
        """Returns aggregated telemetry on root causes of failures."""
        total = len(_FEEDBACK_LOG)
        stage_counts = {stage.value: 0 for stage in FailureTaxonomyStage}
        positive_count = 0
        negative_count = 0

        for r in _FEEDBACK_LOG:
            if r["rating"] == "thumbs_up":
                positive_count += 1
            else:
                negative_count += 1
            if r.get("failure_stage") and r["failure_stage"] in stage_counts:
                stage_counts[r["failure_stage"]] += 1

        return {
            "total_feedback_events": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "satisfaction_rate": (positive_count / total) if total > 0 else 1.0,
            "root_cause_distribution": stage_counts,
        }

    @classmethod
    def list_steward_review_queue(cls) -> list[dict[str, Any]]:
        """Returns all feedback events requiring Data Steward context remediation."""
        return [r for r in _FEEDBACK_LOG if r["status"] == "steward_review_required" or r["rating"] != "thumbs_up"]
