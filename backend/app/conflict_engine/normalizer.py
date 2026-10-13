"""
Claim Decision Key Normalizer.

Transforms raw text, subjects, predicates, objects, and conditions
into a normalized canonical decision key for deterministic conflict evaluation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class NormalizedClaimKey:
    """Canonical, normalized comparison key for an enterprise claim."""
    subject_key: str
    predicate_key: str
    scope_key: Dict[str, str] = field(default_factory=dict)
    condition_key: Dict[str, str] = field(default_factory=dict)
    value_scalar: Optional[float] = None
    value_unit: Optional[str] = None
    modality: str = "POLICY_FACT"
    temporal_window: Tuple[Optional[datetime], Optional[datetime]] = (None, None)


class ClaimNormalizer:
    """Normalizes claims into structured decision keys."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "of", "in", "at", "per", "upon", "under", "for",
        "employees", "employee", "wingify", "staff"
    }

    # Predicate canonicalization mapping
    PREDICATE_CANONICAL_MAP = {
        "has_probationary_notice_duration": "notice_period.probationary_duration",
        "has_confirmed_notice_duration": "notice_period.confirmed_duration",
        "has_notice_duration": "notice_period.duration",
        "request_leave_during_notice_period": "leave.notice_period_request",
        "return": "asset.return_property",
        "cover": "expense.shipping_coverage",
        "deducted_per_asset_management_policy": "deduction.asset_retention",
        "adjusted_from_full_and_final_salary": "deduction.loan_advance",
        "recovered_upon_early_exit": "deduction.wfh_allowance",
        "holds_right_to_recover_short_notice": "discretionary.short_notice_recovery",
        "prohibited_in_any_media": "confidentiality.public_disclosure",
        "prohibited_except_internal_confidential_use": "confidentiality.reproduction",
    }

    @classmethod
    def normalize_entity_tokens(cls, text: str) -> str:
        """Strips punctuation and noise words to create a stable entity key."""
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in clean.split() if t not in cls.STOPWORDS and len(t) >= 2]
        return "_".join(tokens)

    @classmethod
    def extract_scalar_and_unit(cls, object_text: str, claim_text: str) -> Tuple[Optional[float], Optional[str]]:
        """Extracts numerical scalar and normalized measurement unit."""
        search_corpus = f"{object_text} {claim_text}".lower()
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b", search_corpus)
        if match:
            try:
                num = float(match.group(1))
            except ValueError:
                num = None
            raw_unit = match.group(2)
            unit = None
            if raw_unit:
                u_clean = raw_unit.lower().strip()
                if u_clean in ("day", "days"):
                    unit = "days"
                elif u_clean in ("month", "months"):
                    unit = "months"
                elif u_clean in ("year", "years"):
                    unit = "years"
                elif u_clean in ("hour", "hours"):
                    unit = "hours"
                elif u_clean in ("%", "percent"):
                    unit = "%"
                else:
                    unit = u_clean
            return num, unit
        return None, None

    @classmethod
    def normalize_conditions(cls, conditions: list[str], claim_text: str) -> Dict[str, str]:
        """Normalizes free-text conditions into canonical dimension key-value pairs."""
        cond_dict: Dict[str, str] = {}
        combined_text = ((" ".join(conditions) + " " + claim_text)).lower()

        # 1. Employment Status Dimension
        probation_keywords = ("probation", "probationary", "during probation", "probationers")
        confirmed_keywords = ("confirmed", "upon confirmation", "post-confirmation", "confirmed employees")

        is_prob = any(k in combined_text for k in probation_keywords)
        is_conf = any(k in combined_text for k in confirmed_keywords)

        if is_prob and not is_conf:
            cond_dict["employment_status"] = "probationary"
        elif is_conf and not is_prob:
            cond_dict["employment_status"] = "confirmed"

        # 2. Separation Condition
        if "offboarding" in combined_text or "separation" in combined_text or "exit" in combined_text:
            cond_dict["lifecycle_phase"] = "offboarding"

        # 3. Manager Approval Requirement
        if "prior written approval" in combined_text or "manager approval" in combined_text:
            cond_dict["approval_required"] = "manager_written"

        return cond_dict

    @classmethod
    def normalize_scope(cls, subject_text: str, claim_text: str) -> Dict[str, str]:
        """Extracts grade, tier, or role scope dimensions."""
        scope_dict: Dict[str, str] = {}
        combined = f"{subject_text} {claim_text}".lower()

        # Match Grade (e.g. Grade A, Grade B, Grade C, Grade D, Grade E)
        grade_match = re.search(r"\bgrade\s+([a-e])\b", combined)
        if grade_match:
            scope_dict["grade"] = grade_match.group(1).upper()

        # Match Role Category
        if "cxo" in combined:
            scope_dict["category"] = "cxo"
        elif "senior management" in combined:
            scope_dict["category"] = "senior_management"
        elif "middle management" in combined:
            scope_dict["category"] = "middle_management"
        elif "junior management" in combined:
            scope_dict["category"] = "junior_management"
        elif "fellow" in combined:
            scope_dict["category"] = "fellow"

        return scope_dict

    @classmethod
    def build_key(cls, claim: Any) -> NormalizedClaimKey:
        """Constructs a NormalizedClaimKey from a Claim or CandidateClaim object."""
        raw_subj = getattr(claim, "subject", "") or ""
        raw_pred = getattr(claim, "predicate", "") or ""
        raw_obj = getattr(claim, "object", "") or getattr(claim, "object_value", "") or ""
        raw_text = getattr(claim, "claim_text", "") or ""
        raw_conds = getattr(claim, "conditions", []) or []

        # Canonical subject key
        subj_key = cls.normalize_entity_tokens(raw_subj) or cls.normalize_entity_tokens(raw_text[:40])

        # Canonical predicate key
        pred_key = cls.PREDICATE_CANONICAL_MAP.get(raw_pred, raw_pred)

        # Conditions and Scope
        cond_dict = cls.normalize_conditions(raw_conds, raw_text)
        scope_dict = cls.normalize_scope(raw_subj, raw_text)

        # Scalar and Unit
        scalar_val, unit_val = cls.extract_scalar_and_unit(raw_obj, raw_text)

        # Modality
        modality = getattr(claim, "modality", "POLICY_FACT") or "POLICY_FACT"

        return NormalizedClaimKey(
            subject_key=subj_key,
            predicate_key=pred_key,
            scope_key=scope_dict,
            condition_key=cond_dict,
            value_scalar=scalar_val,
            value_unit=unit_val,
            modality=modality,
        )
