"""
Deterministic Pre-LLM Compatibility Gate.

Evaluates whether two claims compete for the exact same decision key.
Filters out complementary rules, orthogonal predicates, and non-overlapping scopes
in O(1) time without consuming LLM tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from app.conflict_engine.normalizer import ClaimNormalizer, NormalizedClaimKey


@dataclass
class CompatibilityOutcome:
    """Outcome of deterministic decision key compatibility evaluation."""
    is_comparable: bool
    reason: str
    relationship: str = "INDEPENDENT"
    details: Dict[str, Any] = field(default_factory=dict)


class CompatibilityGate:
    """
    Deterministic gate that runs prior to LLM contradiction evaluation.
    Prevents false-positive conflicts between complementary conditional rules.
    """

    # Predicate pairs known to be orthogonal / non-competing
    ORTHOGONAL_PREDICATE_PAIRS = {
        ("notice_period.probationary_duration", "notice_period.confirmed_duration"),
        ("has_probationary_notice_duration", "has_confirmed_notice_duration"),
        ("return", "request_leave_during_notice_period"),
        ("asset.return_property", "leave.notice_period_request"),
        ("expense.shipping_coverage", "asset.return_property"),
    }

    @classmethod
    def predicates_compete(cls, pred_a: str, pred_b: str) -> bool:
        """Determines if two predicates govern the same operational property."""
        if pred_a == pred_b:
            return True
        
        pair = (pred_a, pred_b)
        rev_pair = (pred_b, pred_a)
        if pair in cls.ORTHOGONAL_PREDICATE_PAIRS or rev_pair in cls.ORTHOGONAL_PREDICATE_PAIRS:
            return False
            
        # Check canonical prefixes (e.g. notice_period.probationary_duration vs notice_period.confirmed_duration)
        if "probation" in pred_a and "confirmed" in pred_b:
            return False
        if "confirmed" in pred_a and "probation" in pred_b:
            return False

        # If both are general notice duration
        if "notice" in pred_a and "notice" in pred_b:
            return True

        return False

    @classmethod
    def conditions_mutually_exclusive(cls, cond_a: Dict[str, str], cond_b: Dict[str, str]) -> bool:
        """Determines if two condition dictionaries represent mutually exclusive activation sets."""
        # 1. Employment Status Dimension (Probationary vs Confirmed)
        status_a = cond_a.get("employment_status")
        status_b = cond_b.get("employment_status")
        if status_a and status_b and status_a != status_b:
            return True

        return False

    @classmethod
    def scopes_overlap(cls, scope_a: Dict[str, str], scope_b: Dict[str, str]) -> bool:
        """Determines if organizational or grade scopes overlap."""
        # Grade Check
        grade_a = scope_a.get("grade")
        grade_b = scope_b.get("grade")
        if grade_a and grade_b and grade_a != grade_b:
            return False

        # Category Check
        cat_a = scope_a.get("category")
        cat_b = scope_b.get("category")
        if cat_a and cat_b and cat_a != cat_b:
            return False

        return True

    @classmethod
    def evaluate_applicability_overlap(cls, key_a: NormalizedClaimKey, key_b: NormalizedClaimKey) -> CompatibilityOutcome:
        """
        NIST AI RMF 5-Gate Applicability Overlap Check.
        Ensures two claims are only compared if they govern the exact same operational dimension.
        Filters out distinct process stages, payment methods, item conditions, channels, and approval bands.
        """
        # Gate 1: Process Stage Check (Sequential stages are non-competing)
        if key_a.process_stage and key_b.process_stage and key_a.process_stage != key_b.process_stage:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_PROCESS_STAGE",
                relationship="SEQUENTIAL_PROCESS_STAGES",
                details={"stage_a": key_a.process_stage, "stage_b": key_b.process_stage},
            )

        # Gate 2: Payment Method Check (Distinct payment rails have independent settlement cycles)
        if key_a.payment_method and key_b.payment_method and key_a.payment_method != key_b.payment_method:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_PAYMENT_METHOD",
                relationship="DISTINCT_PAYMENT_RAILS",
                details={"payment_a": key_a.payment_method, "payment_b": key_b.payment_method},
            )

        # Gate 3: Policy Domain Check (Subscription policies do not compete with retail return policies)
        if key_a.policy_domain and key_b.policy_domain and key_a.policy_domain != key_b.policy_domain:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_POLICY_DOMAIN",
                relationship="DISTINCT_DOMAINS",
                details={"domain_a": key_a.policy_domain, "domain_b": key_b.policy_domain},
            )
        if (key_a.policy_domain == "subscription" and key_b.item_condition) or (key_b.policy_domain == "subscription" and key_a.item_condition):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_POLICY_DOMAIN",
                relationship="DISTINCT_DOMAINS",
                details={"domain_a": key_a.policy_domain, "domain_b": key_b.policy_domain},
            )

        # Gate 4: Item Condition Check (Deductions vary by returned item condition)
        if key_a.item_condition and key_b.item_condition and key_a.item_condition != key_b.item_condition:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_ITEM_CONDITION",
                relationship="DISTINCT_ITEM_CONDITIONS",
                details={"cond_a": key_a.item_condition, "cond_b": key_b.item_condition},
            )

        # Gate 5: Service / Contact Channel Check (SLA depends on channel)
        if key_a.channel and key_b.channel and key_a.channel != key_b.channel:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_SERVICE_CHANNEL",
                relationship="DISTINCT_CHANNELS",
                details={"channel_a": key_a.channel, "channel_b": key_b.channel},
            )

        # Gate 6: Risk / Abuse Band Check (Different return rate tiers)
        if key_a.risk_band and key_b.risk_band and key_a.risk_band != key_b.risk_band:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_RISK_BANDS",
                relationship="DISTINCT_RISK_TIERS",
                details={"band_a": key_a.risk_band, "band_b": key_b.risk_band},
            )

        # Gate 7: Approval Band Check
        if key_a.approval_band and key_b.approval_band and key_a.approval_band != key_b.approval_band:
            # Check for genuine boundary ambiguity: "under_50" vs "up_to_50"
            is_boundary_ambiguity = (
                {key_a.approval_band, key_b.approval_band} == {"under_50", "up_to_50"} or
                ("under" in key_a.approval_band and "up_to" in key_b.approval_band) or
                ("up_to" in key_a.approval_band and "under" in key_b.approval_band)
            )
            if is_boundary_ambiguity:
                return CompatibilityOutcome(
                    is_comparable=True,
                    reason="GENUINE_BOUNDARY_AMBIGUITY",
                    relationship="BOUNDARY_INCONSISTENCY",
                    details={"band_a": key_a.approval_band, "band_b": key_b.approval_band},
                )
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPROVAL_BANDS",
                relationship="DISTINCT_AUTHORIZATION_TIERS",
                details={"band_a": key_a.approval_band, "band_b": key_b.approval_band},
            )

        return CompatibilityOutcome(
            is_comparable=True,
            reason="OVERLAPPING_APPLICABILITY",
            relationship="APPLICABLE_CANDIDATES",
        )

    @classmethod
    def evaluate_compatibility(cls, claim_a: Any, claim_b: Any) -> CompatibilityOutcome:
        """
        Evaluates whether claim_a and claim_b compete for the exact same decision key.
        Returns a CompatibilityOutcome with machine-readable reasons.
        """
        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        # 0. Multi-dimensional Applicability Overlap Check
        app_outcome = cls.evaluate_applicability_overlap(key_a, key_b)
        if not app_outcome.is_comparable:
            return app_outcome
        if app_outcome.reason == "GENUINE_BOUNDARY_AMBIGUITY":
            return app_outcome

        # 1. Scope Applicability Overlap
        if not cls.scopes_overlap(key_a.scope_key, key_b.scope_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPLICABILITY_SCOPE",
                relationship="DISJOINT_SCOPES",
                details={"scope_a": key_a.scope_key, "scope_b": key_b.scope_key},
            )

        # 2. Mutually Exclusive Condition Dimension
        if cls.conditions_mutually_exclusive(key_a.condition_key, key_b.condition_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="NON_OVERLAPPING_CONDITIONAL_SCOPE",
                relationship="COMPLEMENTARY_CONDITIONAL_RULES",
                details={"condition_a": key_a.condition_key, "condition_b": key_b.condition_key},
            )

        # 3. Predicate Competition Check
        if not cls.predicates_compete(key_a.predicate_key, key_b.predicate_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="ORTHOGONAL_PREDICATES",
                relationship="COMPLEMENTARY_CONDITIONAL_RULES",
                details={"predicate_a": key_a.predicate_key, "predicate_b": key_b.predicate_key},
            )

        # 4. Subject Overlap Check
        if key_a.subject_key != key_b.subject_key:
            # Check token overlap
            tokens_a = set(key_a.subject_key.split("_"))
            tokens_b = set(key_b.subject_key.split("_"))
            if not tokens_a.intersection(tokens_b):
                return CompatibilityOutcome(
                    is_comparable=False,
                    reason="DISTINCT_SUBJECT_ENTITIES",
                    relationship="DISTINCT_ENTITIES",
                    details={"subj_a": key_a.subject_key, "subj_b": key_b.subject_key},
                )

        # All filters passed: Decision keys actively compete!
        return CompatibilityOutcome(
            is_comparable=True,
            reason="COMPETING_DECISION_KEYS",
            relationship="COMPETING_CANDIDATES",
            details={"key_a": key_a, "key_b": key_b},
        )

    @classmethod
    def evaluate_value_conflict(cls, claim_a: Any, claim_b: Any) -> Tuple[bool, str]:
        """
        Evaluates scalar/unit divergence for two claims whose decision keys compete.
        Returns (is_conflict, conflict_type).
        """
        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        # Check boundary ambiguity
        if (key_a.approval_band and key_b.approval_band) and (
            {key_a.approval_band, key_b.approval_band} == {"under_50", "up_to_50"} or
            ("under" in key_a.approval_band and "up_to" in key_b.approval_band) or
            ("up_to" in key_a.approval_band and "under" in key_b.approval_band)
        ):
            return True, "GENUINE_BOUNDARY_AMBIGUITY"

        if key_a.value_scalar is not None and key_b.value_scalar is not None:
            if key_a.value_scalar != key_b.value_scalar:
                # Same unit or units compatible
                if not key_a.value_unit or not key_b.value_unit or key_a.value_unit == key_b.value_unit:
                    return True, "INCOMPATIBLE_NUMERIC_VALUE"
            else:
                return False, "MATCHING_VALUES"

        # Check modality opposition (OBLIGATION vs PROHIBITION)
        mods = {key_a.modality, key_b.modality}
        if "OBLIGATION" in mods and "PROHIBITION" in mods:
            return True, "DEONTIC_OPPOSITION"

        return False, "COMPATIBLE"
