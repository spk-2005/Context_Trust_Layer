"""
Layer 4: Specialized Conversation Parser.
Processes collaboration and issue-tracking platforms (Slack, Teams, Jira comments, GitHub PR reviews, Emails).
Preserves parent-child reply chains, speaker provenance, timestamps, and decision contexts.
"""

from __future__ import annotations

import json
import logging
from typing import Any, List

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit

logger = logging.getLogger(__name__)


class ConversationParser:
    """Specialized parser for chat threads, issue discussions, and comment streams."""

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        units: List[ParsedEvidenceUnit] = []
        payload = envelope.raw_payload

        channel = envelope.locator_metadata.get("channel") or envelope.locator_metadata.get("project") or "general"
        thread_id = envelope.locator_metadata.get("thread_id") or envelope.locator_metadata.get("issue_key") or envelope.asset_id.split("/")[-1]

        messages: list[dict[str, Any]] = []

        # Parse message stream from various structures
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    messages.append(item)
                else:
                    messages.append({"text": str(item)})
        elif isinstance(payload, dict):
            if "messages" in payload and isinstance(payload["messages"], list):
                messages = payload["messages"]
            elif "comments" in payload and isinstance(payload["comments"], list):
                messages = payload["comments"]
            else:
                messages = [payload]
        elif isinstance(payload, str):
            try:
                parsed_json = json.loads(payload)
                if isinstance(parsed_json, list):
                    messages = parsed_json
                elif isinstance(parsed_json, dict):
                    messages = parsed_json.get("messages", [parsed_json])
            except Exception:
                # Text with speaker lines: "Alice: hello\nBob: hi"
                for line in payload.splitlines():
                    if line.strip():
                        if ":" in line:
                            spk, txt = line.split(":", 1)
                            messages.append({"speaker": spk.strip(), "text": txt.strip()})
                        else:
                            messages.append({"text": line.strip()})

        # Process each message into an atomic evidence unit
        for idx, msg in enumerate(messages):
            speaker = (
                msg.get("speaker")
                or msg.get("author")
                or msg.get("user")
                or msg.get("sender")
                or "Unknown Speaker"
            )
            text_body = msg.get("text") or msg.get("body") or msg.get("content") or str(msg)
            timestamp = msg.get("timestamp") or msg.get("created_at") or msg.get("time") or ""
            msg_id = str(msg.get("id") or msg.get("message_id") or f"msg_{idx+1}")
            parent_id = msg.get("parent_id") or msg.get("reply_to")

            formatted_text = f"[{speaker}] {text_body}"
            if timestamp:
                formatted_text = f"({timestamp}) {formatted_text}"

            unit = ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="chat_message",
                content_text=formatted_text,
                structured_data={
                    "speaker": speaker,
                    "raw_text": text_body,
                    "timestamp": timestamp,
                    "message_id": msg_id,
                    "parent_id": parent_id,
                    "channel": channel,
                    "thread_id": thread_id,
                },
                locator={
                    "channel": channel,
                    "thread_id": thread_id,
                    "message_id": msg_id,
                    "speaker": speaker,
                    **envelope.locator_metadata,
                },
                hierarchical_context=[f"Channel: {channel}", f"Thread: {thread_id}", f"Message by {speaker}"],
                sequence_index=idx,
                metadata={"reply_depth": 1 if parent_id else 0},
            )
            units.append(unit)

        quality_metrics = {
            "total_messages": len(units),
            "speakers_detected": len(set(u.structured_data.get("speaker") for u in units)),
            "channel": channel,
            "thread_id": thread_id,
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.CONVERSATION,
            parser_name="ConversationParser",
            units=units,
            completeness_score=1.0,
            quality_metrics=quality_metrics,
        )
