"""
Layer 5: Candidate Discovery Engine ("What might be a claim?").
Scans ParsedEvidenceUnits from Layer 4 and determines eligibility for claim extraction.
Identifies normative assertions, database invariants, schema constraints, table policies, and metric rules.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.extraction.models import ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class CandidateDiscoveryEngine:
    """Discovers claim candidates from Layer 4 parsed evidence units."""

    # Modal verbs and normative policy markers
    MODAL_PATTERN = re.compile(
        r"\b(must|shall|required|requires|mandates?|prohibited|forbidden|cannot|can not|should|enforces?|restricted to|always|never|guarantees?)\b",
        re.IGNORECASE,
    )
    # Thresholds, numerical values, and standard time windows
    THRESHOLD_PATTERN = re.compile(
        r"\b(\d+\s*(?:days?|hours?|minutes?|seconds?|months?|years?|percent|%|bits?|bytes?|ms))\b|\b(AES-?\d+|FIDO2|WebAuthn|MFA|TLS\s*v?\d*\.?\d*|SHA-?\d+)\b",
        re.IGNORECASE,
    )
    # Conversational decision keywords
    DECISION_PATTERN = re.compile(
        r"\b(approv(?:ed|ing|e)|agree|co-sign(?:ed)?|grant(?:ed)?|exempt(?:ion)?|decision|reject(?:ed)?|denied|deployed)\b",
        re.IGNORECASE,
    )

    @classmethod
    def is_candidate(cls, unit: ParsedEvidenceUnit) -> Tuple[bool, ExtractionStrategyType, str]:
        """
        Evaluates an evidence unit.
        Returns (is_candidate, recommended_strategy, reason).
        """
        b_type = unit.block_type
        text = unit.content_text or ""
        s_data = unit.structured_data or {}

        # 1. Structured Database & BSON Records -> Deterministic Schema Extraction
        if b_type in ("database_record", "record_row", "structured_record"):
            # Has data fields or key-value entries
            if s_data.get("flattened_fields") or s_data.get("raw_record") or s_data.get("row_value"):
                return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Database record with typed field invariants."
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Structured operational record."

        # 2. Relational & Schema DDL Definitions -> Deterministic Schema Extraction
        if b_type in ("schema_definition", "column_definition"):
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Relational schema constraint / DDL definition."

        # 3. BI Metric Definitions & Lineage -> Deterministic Schema Extraction
        if b_type in ("metric_definition", "lineage_node", "config_property"):
            return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "BI metric rule or lineage dependency."

        # 4. Structured Table Rows -> Deterministic or Domain Rules
        if b_type == "table_row":
            if s_data.get("columns"):
                return True, ExtractionStrategyType.DETERMINISTIC_SCHEMA, "Structured table matrix row with defined columns."
            return True, ExtractionStrategyType.DOMAIN_RULES, "Table row policy specification."

        # 5. Conversational Decisions & Messages
        if b_type == "chat_message":
            if cls.DECISION_PATTERN.search(text) or cls.MODAL_PATTERN.search(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Conversational decision or policy exemption."
            return False, ExtractionStrategyType.DOMAIN_RULES, "Informal chat message without decision."

        # 6. Document Clauses & Paragraphs
        if b_type in ("clause", "paragraph"):
            has_modal = bool(cls.MODAL_PATTERN.search(text))
            has_threshold = bool(cls.THRESHOLD_PATTERN.search(text))

            if has_modal and has_threshold:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Strict policy clause with modal obligations and numerical thresholds."
            elif has_modal:
                return True, ExtractionStrategyType.LLM_SEMANTIC, "Normative assertion containing modal requirements."
            elif has_threshold and len(text.split()) > 4:
                return True, ExtractionStrategyType.LLM_SEMANTIC, "Factual claim containing quantitative thresholds."
            return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational prose without normative constraints."

        # 7. Headings (context providers, generally not standalone claims)
        if b_type == "heading":
            return False, ExtractionStrategyType.DOMAIN_RULES, "Structural heading without standalone claim."

        return False, ExtractionStrategyType.DOMAIN_RULES, "Unrecognized block type."

    @classmethod
    def discover_candidates(
        cls, units: List[ParsedEvidenceUnit]
    ) -> List[Tuple[ParsedEvidenceUnit, ExtractionStrategyType, str]]:
        """Filters an evidence unit list to only candidate units with assigned extraction strategies."""
        candidates = []
        for u in units:
            eligible, strategy, reason = cls.is_candidate(u)
            if eligible:
                candidates.append((u, strategy, reason))
        return candidates
