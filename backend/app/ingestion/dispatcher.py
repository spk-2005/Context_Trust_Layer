"""
Layer 3: Source Type Detection & Routing Engine.
Routes CanonicalSourceEnvelopes to specialized Layer 4 parsers:
1. Documents & Files (PDF, DOCX, Markdown, HTML, Tables)
2. Structured Data (SQL Rows, MongoDB BSON, JSON/CSV, Relational Schemas)
3. Conversations (Chat Threads, Email Threads, Jira/PR Comments)
4. Metadata & Operational (BI Models, Lineage Graphs, Events, Logs, Configs)
"""

from __future__ import annotations

import logging
import uuid
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope

logger = logging.getLogger(__name__)


class TargetParserCategory(str, Enum):
    """Destination categories corresponding to Layer 4 specialized parsers."""
    DOCUMENTS_AND_FILES = "documents_and_files"
    STRUCTURED_DATA = "structured_data"
    CONVERSATIONS = "conversations"
    METADATA_OPERATIONAL = "metadata_operational"


class RoutingDecision(BaseModel):
    """Outcome of source type detection and destination routing."""
    envelope_id: uuid.UUID
    asset_id: str
    target_parser: TargetParserCategory
    detected_format: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    reason: str
    handler_name: str = "default_handler"


class DeadLetterEnvelope(BaseModel):
    """Captured malformed or un-routable envelope for debugging and audit."""
    envelope_id: uuid.UUID
    asset_id: str
    error_message: str
    source_family: str
    captured_at: str


class SourceTypeDetector:
    """
    Introspects envelope metadata, MIME type, schema definition, and payload characteristics
    to accurately detect the parser destination.
    """

    @staticmethod
    def detect(envelope: CanonicalSourceEnvelope) -> RoutingDecision:
        fmt = (envelope.native_format or "").lower().strip()
        fam = envelope.source_family
        intent = envelope.source_intent
        asset_id = (envelope.asset_id or "").lower()
        payload = envelope.raw_payload

        # 1. Check for Conversation Family (Slack, Teams, Jira comments, PR reviews)
        if (
            fam == SourceFamily.ISSUE_TRACKER
            or fam == SourceFamily.CONVERSATION
            or "slack://" in asset_id
            or "teams://" in asset_id
            or "comment" in asset_id
            or "thread" in asset_id
            or fmt in ("chat_thread", "email_thread", "slack_message", "jira_comment")
        ):
            return RoutingDecision(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                target_parser=TargetParserCategory.CONVERSATIONS,
                detected_format=fmt or "conversation",
                confidence=0.98,
                reason="Identified as conversational/issue discussion thread from source family and asset URI.",
                handler_name="conversation_parser",
            )

        # 2. Check for Metadata & Operational (BI models, lineage graphs, metrics, events/logs)
        if (
            intent in (SourceIntent.ANALYTICS_METRIC, SourceIntent.LINEAGE_GRAPH)
            or fmt in ("bi_model", "lineage_graph", "telemetry_log", "metric_definition")
            or "dbt://" in asset_id
            or "looker://" in asset_id
        ):
            return RoutingDecision(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                target_parser=TargetParserCategory.METADATA_OPERATIONAL,
                detected_format=fmt or "metadata_operational",
                confidence=0.95,
                reason="Identified as operational/analytics metadata or lineage graph.",
                handler_name="metadata_operational_parser",
            )

        # 3. Check for Structured Data (SQL schemas, tables, MongoDB BSON, JSON/CSV/XML)
        if (
            fam in (SourceFamily.RELATIONAL, SourceFamily.DOCUMENT_DB, SourceFamily.STRUCTURED)
            or fmt in ("sql_schema", "json_schema", "json", "csv", "xml", "parquet", "bson", "table_row")
            or "postgres://" in asset_id
            or "mongodb://" in asset_id
            or "mysql://" in asset_id
            or isinstance(payload, (dict, list))
        ):
            return RoutingDecision(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                target_parser=TargetParserCategory.STRUCTURED_DATA,
                detected_format=fmt or "structured_data",
                confidence=0.99,
                reason="Identified as relational or document-based structured data (database/JSON/CSV).",
                handler_name="structured_data_parser",
            )

        # 4. Default to Documents & Files (PDF, Markdown, DOCX, HTML, plain text)
        return RoutingDecision(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            target_parser=TargetParserCategory.DOCUMENTS_AND_FILES,
            detected_format=fmt or "document_text",
            confidence=0.95,
            reason="Identified as narrative document, policy, or file asset.",
            handler_name="document_ast_parser",
        )


class SourceEnvelopeRouter:
    """
    Central dispatcher for Layer 3.
    Resolves destinations, invokes registered parser handlers, tracks telemetry, and isolates failures.
    """

    def __init__(self):
        self._handlers: Dict[TargetParserCategory, Callable[[CanonicalSourceEnvelope], Coroutine[Any, Any, Any]]] = {}
        self._dead_letters: List[DeadLetterEnvelope] = []
        self._telemetry: Dict[str, int] = {
            "routed_documents_and_files": 0,
            "routed_structured_data": 0,
            "routed_conversations": 0,
            "routed_metadata_operational": 0,
            "failed_dispatches": 0,
        }

    def register_parser_handler(
        self,
        category: TargetParserCategory,
        handler: Callable[[CanonicalSourceEnvelope], Coroutine[Any, Any, Any]],
    ) -> None:
        """Allows Layer 4 parsers to register their execution callbacks."""
        self._handlers[category] = handler
        logger.info("Registered Layer 4 parser handler for category: %s", category.value)

    def route(self, envelope: CanonicalSourceEnvelope) -> RoutingDecision:
        """Detects and returns the deterministic routing decision for an envelope."""
        return SourceTypeDetector.detect(envelope)

    async def dispatch(self, envelope: CanonicalSourceEnvelope) -> Any:
        """Routes and invokes the registered Layer 4 parser for a single envelope."""
        decision = self.route(envelope)
        
        # Update routing telemetry
        counter_key = f"routed_{decision.target_parser.value}"
        if counter_key in self._telemetry:
            self._telemetry[counter_key] += 1

        handler = self._handlers.get(decision.target_parser)
        if not handler:
            logger.debug(
                "No custom handler registered for %s; returning envelope with decision.",
                decision.target_parser.value,
            )
            return {
                "status": "routed",
                "envelope_id": str(envelope.envelope_id),
                "asset_id": envelope.asset_id,
                "target_parser": decision.target_parser.value,
                "detected_format": decision.detected_format,
                "confidence": decision.confidence,
                "reason": decision.reason,
            }

        try:
            return await handler(envelope)
        except Exception as exc:
            logger.error(
                "Dispatch failed for envelope %s (asset %s): %s",
                envelope.envelope_id,
                envelope.asset_id,
                str(exc),
                exc_info=True,
            )
            self._telemetry["failed_dispatches"] += 1
            self._dead_letters.append(
                DeadLetterEnvelope(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    error_message=str(exc),
                    source_family=envelope.source_family.value if hasattr(envelope.source_family, "value") else str(envelope.source_family),
                    captured_at=envelope.captured_at.isoformat(),
                )
            )
            raise exc

    async def batch_dispatch(
        self,
        envelopes: Sequence[CanonicalSourceEnvelope],
    ) -> Dict[str, Any]:
        """Dispatches a batch of canonical envelopes and aggregates decisions and results."""
        results: List[Any] = []
        routing_decisions: List[Dict[str, Any]] = []

        for env in envelopes:
            decision = self.route(env)
            routing_decisions.append({
                "envelope_id": str(env.envelope_id),
                "asset_id": env.asset_id,
                "source_family": env.source_family.value if hasattr(env.source_family, "value") else str(env.source_family),
                "target_parser": decision.target_parser.value,
                "detected_format": decision.detected_format,
                "confidence": decision.confidence,
                "reason": decision.reason,
            })
            res = await self.dispatch(env)
            results.append(res)

        return {
            "total_envelopes": len(envelopes),
            "routing_decisions": routing_decisions,
            "results": results,
            "telemetry": dict(self._telemetry),
            "dead_letter_count": len(self._dead_letters),
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns routing metrics and dead-letter statistics."""
        return {
            "telemetry": dict(self._telemetry),
            "dead_letters": [d.model_dump() for d in self._dead_letters[-20:]],
            "registered_handlers": [k.value for k in self._handlers.keys()],
        }


# Global singleton instance for platform-wide dispatch
global_envelope_router = SourceEnvelopeRouter()
