"""
Layer 4: Universal Evidence Data Model.
Standardizes parsed content across all specialized source-family parsers
(Document, Structured Data, Conversations, and Metadata) into strongly-typed evidence units.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.db.enums import SourceFamily


class ContentRole(str, Enum):
    """Controlled semantic classification for document blocks and evidence units."""
    POLICY_RULE = "policy_rule"           # Operative normative rule, obligation, entitlement, threshold, matrix
    DEFINITION = "definition"             # Glossary term, lexical definition, "means", "refers to"
    PROCEDURE = "procedure"               # Step-by-step workflow, administrative process, submission instruction
    FAQ = "faq"                           # Frequently asked questions & answers (Q&A pair)
    EXAMPLE = "example"                   # Illustrative worked scenario, hypothetical calculation
    REVISION_HISTORY = "revision_history" # Version changelog, approval metadata, revision table, sign-off block
    HEADING = "heading"                   # Document header, section title, structural outline divider
    CONTACT_INFO = "contact_info"         # Support desk, HR email, contact phone number, address


class ParsedEvidenceUnit(BaseModel):
    """
    Atomic unit of parsed evidence (e.g., a policy clause, a database row, a chat message).
    Preserves exact source locators and native structured data for zero-hallucination grounding.
    """
    unit_id: str = Field(..., description="Deterministic unique identifier for this evidence unit")
    envelope_id: uuid.UUID = Field(..., description="Parent Layer 3 CanonicalSourceEnvelope identifier")
    asset_id: str = Field(..., description="Native external asset identifier")
    block_type: str = Field(..., description="Semantic block type (clause, heading, table_row, record_field, chat_message, metric_rule)")
    content_role: ContentRole = Field(default=ContentRole.POLICY_RULE, description="Classified semantic role of this content unit")
    is_canonical: bool = Field(default=True, description="False if illustrative example, revision log, heading, or contact metadata")
    content_text: str = Field(..., description="Normalized textual representation suitable for candidate claim extraction")
    structured_data: dict[str, Any] = Field(default_factory=dict, description="Pristine native typed values, column schemas, or JSON paths")
    locator: dict[str, Any] = Field(default_factory=dict, description="Fine-grained source-specific locator coordinates")
    hierarchical_context: list[str] = Field(default_factory=list, description="Breadcrumb ancestry (e.g. ['Section 2', 'Clause 2.1'])")
    content_hash: str = Field(..., description="Deterministic SHA-256 hash of this atomic unit")
    sequence_index: int = Field(default=0, description="Order of appearance in the original asset")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parser-specific extraction metadata")

    @classmethod
    def create(
        cls,
        envelope_id: uuid.UUID,
        asset_id: str,
        block_type: str,
        content_text: str,
        structured_data: dict[str, Any] | None = None,
        locator: dict[str, Any] | None = None,
        hierarchical_context: list[str] | None = None,
        sequence_index: int = 0,
        metadata: dict[str, Any] | None = None,
        content_role: ContentRole | str | None = None,
        is_canonical: bool | None = None,
    ) -> ParsedEvidenceUnit:
        text_clean = (content_text or "").strip()
        data = structured_data or {}

        # Resolve ContentRole
        resolved_role = ContentRole.POLICY_RULE
        if content_role:
            try:
                resolved_role = ContentRole(content_role) if isinstance(content_role, str) else content_role
            except ValueError:
                resolved_role = ContentRole.POLICY_RULE
        elif block_type == "heading":
            resolved_role = ContentRole.HEADING

        # Resolve canonicity: definitions, examples, history, headings, FAQs, and contact info are non-canonical
        if is_canonical is None:
            if resolved_role in (
                ContentRole.DEFINITION,
                ContentRole.EXAMPLE,
                ContentRole.REVISION_HISTORY,
                ContentRole.HEADING,
                ContentRole.CONTACT_INFO,
                ContentRole.FAQ,
            ):
                resolved_canonical = False
            else:
                resolved_canonical = True
        else:
            resolved_canonical = is_canonical

        # Calculate unit hash
        hash_input = f"{asset_id}:{block_type}:{resolved_role.value}:{text_clean}:{json.dumps(data, sort_keys=True, default=str)}"
        unit_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        unit_id = f"{envelope_id}:{sequence_index}:{unit_hash[:12]}"

        return cls(
            unit_id=unit_id,
            envelope_id=envelope_id,
            asset_id=asset_id,
            block_type=block_type,
            content_role=resolved_role,
            is_canonical=resolved_canonical,
            content_text=text_clean,
            structured_data=data,
            locator=locator or {},
            hierarchical_context=hierarchical_context or [],
            content_hash=unit_hash,
            sequence_index=sequence_index,
            metadata=metadata or {},
        )


class ParsedEvidenceResult(BaseModel):
    """
    Standard evidence bundle produced by any Layer 4 specialized parser for an envelope.
    Tracks parsing completeness and quality metrics.
    """
    envelope_id: uuid.UUID
    asset_id: str
    source_family: SourceFamily
    parser_name: str
    units: List[ParsedEvidenceUnit] = Field(default_factory=list)
    completeness_score: float = Field(ge=0.0, le=1.0, default=1.0, description="Ratio of asset content successfully parsed without error")
    quality_metrics: dict[str, Any] = Field(default_factory=dict, description="Parsing fidelity metrics (e.g. tables parsed, char count)")
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "source_family": self.source_family.value if hasattr(self.source_family, "value") else str(self.source_family),
            "parser_name": self.parser_name,
            "total_units": len(self.units),
            "completeness_score": self.completeness_score,
            "quality_metrics": self.quality_metrics,
            "parsed_at": self.parsed_at.isoformat(),
            "units": [u.model_dump() for u in self.units],
        }
