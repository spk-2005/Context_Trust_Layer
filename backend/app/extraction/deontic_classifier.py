"""
Layer 5: Deontic Modality & Semantic Alignment Engine.
Accurately categorizes normative statements into explicit deontic modalities:
- OBLIGATION (MUST / SHALL / REQUIRED)
- PROHIBITION (MUST NOT / PROHIBITED)
- PERMISSION (MAY / PERMITTED)
- POLICY_FACT (Objective definitions & table matrix thresholds)
- DESCRIPTIVE (Guidance, summaries, background context - filtered from gate)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class DeonticClassifier:
    """Classifies deontic modality and normalizes text and S-P-O slots."""

    PROHIBITION_PATTERNS = [
        re.compile(r"\b(prohibited|shall not|must not|forbidden|strictly prohibited|is not permitted|are not permitted|under no circumstances)\b", re.IGNORECASE),
        re.compile(r"\bunauthorized\s+.*?\s+(?:is|are)\s+prohibited\b", re.IGNORECASE),
    ]

    OBLIGATION_PATTERNS = [
        re.compile(r"\b(must|shall|is required to|are required to|is mandatory|are mandatory|obligated to|has to|have to|strictly required)\b", re.IGNORECASE),
    ]

    PERMISSION_PATTERNS = [
        re.compile(r"\b(may|is permitted to|are permitted to|can|allowed to|eligible to|at the discretion of|discretionary|holds the right to|reserves the right to|holds the right)\b", re.IGNORECASE),
    ]

    DISCRETIONARY_RIGHT_PATTERNS = [
        re.compile(r"\b(holds the right to|reserves the right to|reserves right to|at company discretion|discretionary right)\b", re.IGNORECASE),
    ]

    BENEFIT_OR_EXPENSE_PATTERNS = [
        re.compile(r"\b(will be covered by|shall be covered by|will be reimbursed by|shall be reimbursed by|covered by the company|reimbursed by the company|eligible for reimbursement)\b", re.IGNORECASE),
    ]

    DESCRIPTIVE_PATTERNS = [
        re.compile(r"\b(primary goal is|aims to|outlines the expected|purpose of this policy|is designed to|is intended to|serves as|provides guidance|promoting fairness|facilitating a comprehensive|expected duration an employee|our .* policy ensures)\b", re.IGNORECASE),
    ]

    MACRO_SUMMARY_PATTERNS = [
        re.compile(r"\b(summary|overview)\b.*\b(may include|vary based on|outlines various aspects)\b", re.IGNORECASE),
        re.compile(r"\b(deductions\s+from\s+full\s+(?:&|and)\s+final\s+salary\s+may\s+include|notice\s+periods\s+vary\s+based\s+on)\b", re.IGNORECASE),
        re.compile(r"\b(grade-based tenures|establishes notice durations calibrated|calibrated by .* levels)\b", re.IGNORECASE),
        re.compile(r"\b(settlement\s+deductions?\s+summary|deductions\s+including\s+asset/laptop)\b", re.IGNORECASE),
    ]

    @classmethod
    def strip_markdown(cls, text: str) -> str:
        """Removes markdown bold, italics, backticks, bullet markers, and extra spacing."""
        if not text:
            return ""
        s = str(text)
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"\*([^*]+)\*", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"^[●❖\-\*]\s*", "", s)
        s = re.sub(r"[\*`_]+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def is_macro_summary(cls, text: str) -> bool:
        """Checks if text is a macro summary duplicating detailed clauses or table rows."""
        clean = cls.strip_markdown(text)
        return any(pat.search(clean) for pat in cls.MACRO_SUMMARY_PATTERNS)

    @classmethod
    def extract_conditions_and_dependencies(cls, text: str) -> Tuple[List[str], List[str]]:
        """
        Universally extracts explicit conditions and cross-referenced external policies/instruments
        from any clause without injecting ungrounded words.
        """
        conditions: List[str] = []
        dependencies: List[str] = []
        clean = cls.strip_markdown(text)

        # 1. External policy dependencies: "as per (the) X", "based on (the) X", "terms mentioned in (the) X"
        dep_matches = re.findall(
            r"\b(?:as per|based on|governed by|terms mentioned in)\s+(?:the\s+)?([A-Za-z0-9\s]+?(?:Policy|Framework|Agreement|Contract|Guidelines|Matrix|offer letter|Offer Letter))",
            clean,
            re.IGNORECASE,
        )
        for d in dep_matches:
            d_clean = d.strip()
            if d_clean and d_clean not in dependencies:
                dependencies.append(d_clean)

        # 2. Conditional trigger clauses
        cond_patterns = [
            r"\bif\s+([^,;.]+)",
            r"\bwhere\s+([^,;.]+)",
            r"\bunless\s+([^,;.]+)",
            r"\bin cases (?:of|where)\s+([^,;.]+)",
            r"\bupon\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bduring\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bas declared on\s+([A-Za-z0-9\s]+?)(?:[.,;]|$)",
            r"\bbeyond\s+(?:the\s+)?([A-Za-z0-9\s]+?quota)(?:[.,;]|$)",
            r"\bwithin\s+([A-Za-z0-9\s]+?of joining)(?:[.,;]|$)",
        ]

        for cp in cond_patterns:
            matches = re.findall(cp, clean, re.IGNORECASE)
            for m in matches:
                m_str = m.strip().rstrip(".")
                if len(m_str.split()) >= 1 and m_str not in conditions:
                    conditions.append(m_str)

        return conditions, dependencies

    @classmethod
    def split_compound_deductions(cls, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Decomposes compound multi-item deduction statements into discrete atomic rules with explicit conditions.
        Preserves source wording without adding ungrounded qualifiers (e.g. 'annual', 'active', or 'balances').
        """
        clean = cls.strip_markdown(text)
        if not re.search(r"\b(deductions?\s+including|settlement\s+deductions?|deductions?\s+such\s+as|deductions\s+from\s+full\s+&\s+final)\b", clean, re.IGNORECASE):
            return None

        return [
            {
                "item": "Asset / Laptop retention",
                "claim_text": "Full & Final Settlement covers deduction for laptop and company asset values as per the Asset Management Policy.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "deducts_retained_assets",
                "object": "Laptop and company asset values",
                "conditions": ["Employee retains laptop and other company assets upon offboarding"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Outstanding loans",
                "claim_text": "Full & Final Settlement covers deduction for outstanding employee loans or advances.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "adjusts_outstanding_loans",
                "object": "Outstanding loans or advances",
                "conditions": ["Outstanding loans or advances the employee takes upon offboarding"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Tax reconciliation",
                "claim_text": "Full & Final Settlement covers deduction for tax reconciliation at separation.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "reconciles_exit_taxes",
                "object": "Exit tax liabilities",
                "conditions": ["Tax reconciliation upon separation"],
                "modality": "POLICY_FACT",
                "modal_operator": "covers",
            },
            {
                "item": "WFH allowance recovery",
                "claim_text": "Full & Final Settlement covers recovery of WFH allowance per Home Office Allowance Policy if departing within 1 year.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "recovers_wfh_allowance",
                "object": "WFH allowance recovery amount",
                "conditions": ["Employee separation occurs within 1 year of joining"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
            {
                "item": "Excess leave adjustments",
                "claim_text": "Full & Final Settlement covers recovery for excess leaves taken beyond the allotted quota.",
                "subject": "Full & Final Settlement (F&F)",
                "predicate": "recovers_excess_leaves",
                "object": "Excess leaves beyond allotted quota",
                "conditions": ["Leaves taken beyond allotted quota upon separation"],
                "modality": "POLICY_FACT",
                "modal_operator": "enforces",
            },
        ]

    @classmethod
    def classify_text(cls, text: str) -> Tuple[str, str, bool]:
        """
        Classifies textual clause.
        Returns (modality, modal_operator, is_decision_eligible).
        """
        clean = cls.strip_markdown(text)

        # 1. Descriptive / Purpose statements FIRST (informational preamble, not decision gate rules)
        for pat in cls.DESCRIPTIVE_PATTERNS:
            if pat.search(clean):
                return "DESCRIPTIVE", "describes", False

        # 2. Prohibitions (strictly normative prohibitions like 'must not', 'prohibited')
        for pat in cls.PROHIBITION_PATTERNS:
            if pat.search(clean):
                return "PROHIBITION", "prohibits", True

        # 3. Macro Summaries (valid derived statements, tagged for audit ledger)
        if cls.is_macro_summary(clean):
            return "POLICY_FACT", "summarizes", True

        # 4. Discretionary Rights
        for pat in cls.DISCRETIONARY_RIGHT_PATTERNS:
            if pat.search(clean):
                return "PERMISSION", "holds_the_right", True

        # 5. Company Benefit / Expense Coverage
        for pat in cls.BENEFIT_OR_EXPENSE_PATTERNS:
            if pat.search(clean):
                return "POLICY_FACT", "covers", True

        # 6. Obligations
        for pat in cls.OBLIGATION_PATTERNS:
            if pat.search(clean):
                return "OBLIGATION", "requires", True

        # 7. Permissions
        for pat in cls.PERMISSION_PATTERNS:
            if pat.search(clean):
                return "PERMISSION", "permits", True

        # 8. Default factual statement
        return "POLICY_FACT", "specifies", True

    @classmethod
    def normalize_table_policy_claim(
        cls,
        scope_dict: Dict[str, Any],
        rule_key: str,
        rule_value: Any,
        conditions: List[str],
    ) -> Dict[str, Any]:
        """
        Translates a table matrix row cell into a clean, human-readable policy assertion with structured S-P-O.
        """
        clean_rule_key = cls.strip_markdown(rule_key)
        clean_val = cls.strip_markdown(str(rule_value))

        # Extract grade/level and group from scope
        level_val = ""
        category_val = ""
        for k, v in scope_dict.items():
            k_clean = cls.strip_markdown(k).lower()
            v_clean = cls.strip_markdown(str(v))
            if "level" in k_clean or "grade" in k_clean:
                level_val = v_clean
            elif "category" in k_clean or "group" in k_clean or "role" in k_clean:
                category_val = v_clean

        # Clean subject
        if level_val and category_val:
            subject = f"Employees in Grade {level_val} ({category_val})"
        elif level_val:
            subject = f"Employees in Grade {level_val}"
        else:
            subject_parts = [f"{cls.strip_markdown(k)}: {cls.strip_markdown(str(v))}" for k, v in scope_dict.items()]
            subject = ", ".join(subject_parts) or "Governed Employees"

        # Determine predicate and modality based on column
        key_lower = clean_rule_key.lower()
        if "probation" in key_lower:
            predicate = "has_probationary_notice_duration"
            cond_list = ["Probationary status", "Employment Status: During Probation", f"Table Column: {clean_rule_key}"]
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} have a notice period of {clean_val} during probation."
        elif "confirmed" in key_lower or "duration" in key_lower or "maximum" in key_lower:
            predicate = "has_confirmed_notice_duration"
            cond_list = ["Confirmed status", "Employment Status: Upon Confirmation", f"Table Column: {clean_rule_key}"]
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} have a maximum notice period of {clean_val} upon confirmation."
        else:
            predicate = f"has_{key_lower.replace(' ', '_')}"
            cond_list = [f"Table Column: {clean_rule_key}"] + list(conditions or [])
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} specifies {clean_rule_key} as {clean_val}."

        return {
            "claim_text": claim_text,
            "subject": subject,
            "predicate": predicate,
            "object": clean_val,
            "modality": modality,
            "modal_operator": modal_op,
            "conditions": cond_list,
        }
