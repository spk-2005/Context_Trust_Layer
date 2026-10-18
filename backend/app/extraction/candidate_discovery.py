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
        r"\b(must|shall|required|requires|mandates?|prohibited|forbidden|should|enforces?|restricted to|always|never|guarantees?|holds the right|reserves the right|permitted|may|will not be granted|not be granted|will not grant|will be made|cannot)\b",
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
    # Payroll deductions and financial adjustments
    DEDUCTION_RECOVERY_PATTERN = re.compile(
        r"\b(deducted|deductions?|recovered|recovery|adjusted|reconciliation|clawback|holds the right to recover)\b",
        re.IGNORECASE,
    )
    # Company benefit or expense coverage
    BENEFIT_OR_EXPENSE_PATTERN = re.compile(
        r"\b(covered by|shipping costs?|reimburse|reimbursed|allowance)\b",
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

        # 4. Structured Table Rows -> Table-Aware Extraction
        if b_type == "table_row":
            table_type = s_data.get("table_type")
            cols = s_data.get("columns", {})
            col_keys_lower = [str(k).lower().strip() for k in cols.keys()]

            # Filter 4A: Revision History metadata (routed to document provenance)
            if table_type == "revision_history" or (
                any("ver" in k or "revision" in k for k in col_keys_lower)
                and any("date" in k or "description" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is document revision history metadata; routed to document provenance."

            # Filter 4B: Table of Contents / Outline (routed to document structure)
            if table_type == "table_of_contents" or (
                any("section" in k for k in col_keys_lower)
                and any("title" in k or "topic" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is table of contents/section outline; routed to document structure."

            # Filter 4C: Approver / Sign-off log (routed to authority record)
            if table_type == "approver_signoff" or (
                any("role" in k or "sign" in k for k in col_keys_lower)
                and any("name" in k or "designation" in k for k in col_keys_lower)
            ):
                return False, ExtractionStrategyType.TABLE_AWARE, "Table row is document approver sign-off metadata; routed to document authority record."

            # Eligible: Policy Matrix (e.g. Grade Notice Duration Matrix)
            if s_data.get("is_ambiguous"):
                return True, ExtractionStrategyType.TABLE_AWARE, "Table row policy matrix with ambiguous/merged cell layout requiring review."
            if cols:
                return True, ExtractionStrategyType.TABLE_AWARE, "Structured policy matrix row with defined columns."
            return True, ExtractionStrategyType.TABLE_AWARE, "Table row policy specification."

        # 5. Conversational Decisions & Messages
        if b_type == "chat_message":
            if cls.DECISION_PATTERN.search(text) or cls.MODAL_PATTERN.search(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Conversational decision or policy exemption."
            return False, ExtractionStrategyType.DOMAIN_RULES, "Informal chat message without decision."

        # Chinese Deontic Modal Check (DOC-068) - Gated by feature flag
        from app.core.multilingual import is_multilingual_enabled
        if is_multilingual_enabled("zh-CN"):
            if any("\u4e00" <= ch <= "\u9fff" for ch in text) and any(m in text for m in ("\u4e0d\u5f97", "\u5e94\u5f53", "\u5fc5\u987b", "\u5e94", "\u6709\u6743", "\u53ef\u4ee5")):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Chinese contract deontic policy assertion."

        # 6. Document Clauses & Paragraphs
        if b_type in ("clause", "paragraph"):
            from app.extraction.deontic_classifier import DeonticClassifier
            from app.ingestion.parsers.evidence_model import ContentRole

            # Filter out FAQ questions and introductory context upfront
            unit_role = getattr(unit, "content_role", None)
            if unit_role in (ContentRole.FAQ_QUESTION, ContentRole.INTRODUCTORY_CONTEXT, ContentRole.DOCUMENT_METADATA) or text.strip().endswith("?"):
                return False, ExtractionStrategyType.DOMAIN_RULES, "Inquiry question or introductory context; non-canonical context."

            modality, _, is_decision_eligible = DeonticClassifier.classify_text(text)

            # Filter out purely descriptive statements (e.g. "The primary goal is to provide clear guidance...")
            if not is_decision_eligible or modality == "DESCRIPTIVE":
                return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational guidance or purpose statement; filtered from decision gate."

            # Eligible: Macro summary statement summarizing table policy rules or high-level settlement categories
            if DeonticClassifier.is_macro_summary(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Derived summary statement summarizing table policy rules."

            # Eligible: Compound financial/settlement deductions requiring decomposition (fallback for concise docs)
            if DeonticClassifier.split_compound_deductions(text):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Financial settlement and deduction rules requiring atomic decomposition."

            # Eligible: Dedicated deduction and recovery clauses (e.g. laptop retention, loans, tax deductions)
            if cls.DEDUCTION_RECOVERY_PATTERN.search(text) and len(text.split()) > 4:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Payroll deduction or financial recovery policy clause."

            # Eligible: HR termination, severance, or notice policy clauses
            if re.search(r"\b(?:minimum of two weeks|written notice|resignation|final paycheck|position elimination|severance pay|pay instead of notice|pay in (?:lieu|place) of notice)\b", text, re.IGNORECASE):
                return True, ExtractionStrategyType.DOMAIN_RULES, "HR termination, notice, or severance policy clause."

            # Eligible: Policy Effective Date specification
            if re.search(r"\bEffective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\b|\beffective\s+date\b", text, re.IGNORECASE):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Policy effective date specification."

            # Eligible: Company benefit or expense coverage (e.g. shipping costs covered)
            if cls.BENEFIT_OR_EXPENSE_PATTERN.search(text) and len(text.split()) > 4:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Company expense or benefit policy clause."

            # Eligible: Product return exclusions and specifications
            if any(w in text.lower() for w in ("clearly personalized", "made to your specifications", "custom-made", "cannot be returned", "inseparably mixed", "unsealed after delivery")):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Product return exclusion or specification restriction."

            has_modal = bool(cls.MODAL_PATTERN.search(text))
            has_threshold = bool(cls.THRESHOLD_PATTERN.search(text))

            if modality == "PROHIBITION":
                return True, ExtractionStrategyType.DOMAIN_RULES, "Strict policy prohibition clause."
            elif has_modal and has_threshold:
                return True, ExtractionStrategyType.DOMAIN_RULES, "Strict policy clause with modal obligations and numerical thresholds."
            elif has_modal or modality in ("OBLIGATION", "PERMISSION"):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Normative assertion containing modal requirements or discretionary permissions."
            elif has_threshold and len(text.split()) > 4:
                return True, ExtractionStrategyType.LLM_SEMANTIC, "Factual claim containing quantitative thresholds."
            return False, ExtractionStrategyType.LLM_SEMANTIC, "Informational prose without normative constraints."

        # 7. Headings (context providers, generally not standalone claims)
        if b_type == "heading":
            if cls.MODAL_PATTERN.search(text) or (len(text.split()) > 6 and any(w in text.lower() for w in ("resignation", "notice", "elimination", "severance", "policy", "employees", "contract", "remuneration", "entitled", "maintained"))):
                return True, ExtractionStrategyType.DOMAIN_RULES, "Composite heading with actionable policy prose."
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
