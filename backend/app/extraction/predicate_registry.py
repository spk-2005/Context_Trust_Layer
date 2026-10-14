"""
Canonical Predicate Registry (Sprint 2 / Layer 5-7).
Defines versioned, controlled enterprise policy predicates to prevent
unconstrained generic verbs ('specifies', 'be', 'defines', 'override')
from being approved as canonical policy assertions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Set, Tuple


class CanonicalPredicate(str, Enum):
    """Controlled canonical predicate vocabulary for enterprise governance."""

    # Policy Entitlements & Windows
    HAS_RETURN_WINDOW = "has_return_window"
    HAS_RETURN_DEADLINE = "has_return_deadline"
    HAS_REFUND_PERCENTAGE = "has_refund_percentage"
    HAS_REFUND_ELIGIBILITY = "has_refund_eligibility"
    HAS_REFUND_METHOD = "has_refund_method"
    HAS_POSTING_DURATION = "has_posting_duration"
    HAS_STAGE_DURATION = "has_stage_duration"

    # Cancellation States & Post-Shipment Outcomes
    HAS_CANCELLATION_ELIGIBILITY = "has_cancellation_eligibility"
    HAS_CANCELLATION_RULE = "has_cancellation_rule"
    HAS_CANCELLATION_REFUND_OUTCOME = "has_cancellation_refund_outcome"
    HAS_CANCELLATION_REFUND_TIMING = "has_cancellation_refund_timing"
    HAS_POST_SHIPMENT_RESOLUTION_PATH = "has_post_shipment_resolution_path"
    HAS_POST_DELIVERY_RESOLUTION_PATH = "has_post_delivery_resolution_path"

    # Warranty Obligations
    HAS_WARRANTY_PERIOD = "has_warranty_period"
    HAS_WARRANTY_REMEDY = "has_warranty_remedy"

    # Authorizations & Risk Gates
    REQUIRES_APPROVAL_ROLE = "requires_approval_role"
    REQUIRES_FRAUD_REVIEW = "requires_fraud_review"

    # Contact Channels & Operational Service Levels
    HAS_CONTACT_CHANNEL = "has_contact_channel"
    HAS_CONTACT_HOURS = "has_contact_hours"
    HAS_CONTACT_PHONE = "has_contact_phone"
    HAS_CONTACT_EMAIL = "has_contact_email"
    HAS_CONTACT_ADDRESS = "has_contact_address"
    HAS_SERVICE_LEVEL_TARGET = "has_service_level_target"

    # Definitions, References & Structured Options
    HAS_INTERNAL_POLICY_REFERENCE = "has_internal_policy_reference"
    HAS_DEFINITION = "has_definition"
    HAS_RESOLUTION_OPTION_DETAILS = "has_resolution_option_details"
    HAS_RESOLUTION_PATH = "has_resolution_path"
    HAS_BILLING_SCHEDULE = "has_billing_schedule"
    HAS_RETURN_SHIPPING_RULE = "has_return_shipping_rule"
    HAS_RETURN_LABEL_COST = "has_return_label_cost"
    HAS_DUTIES_AND_TAXES_RULE = "has_duties_and_taxes_rule"
    HAS_REFUND_ALLOCATION_RULE = "has_refund_allocation_rule"
    HAS_IDENTITY_VERIFICATION_REQUIREMENT = "has_identity_verification_requirement"
    HAS_PROVIDER_GOVERNED_TIMELINE = "has_provider_governed_timeline"
    HAS_EXAMPLE_VALUE = "has_example_value"

    # Normalized Domain Behaviors & Atomic Criteria
    RESPONSIBLE_FOR_SHIPPING_COSTS = "responsible_for_shipping_costs"
    COVERS_SHIPPING_COSTS = "covers_shipping_costs"
    MAY_OVERRIDE_STANDARD_TERMS = "may_override_standard_terms"
    CAN_INITIATE_RETURN = "can_initiate_return"
    MUST_VERIFY_REFUND_CONDITIONS = "must_verify_refund_conditions"
    REQUIRES_RETURN_WITHIN_APPLICABLE_WINDOW = "requires_return_within_applicable_window"
    MUST_BE_IN_ORIGINAL_CONDITION = "must_be_in_original_condition"
    REQUIRES_VERIFIABLE_ORDER_OR_PURCHASE_PROOF = "requires_verifiable_order_or_purchase_proof"


class PredicateRegistry:
    """
    Registry for validating, normalizing, and shielding enterprise policy predicates.
    """

    CANONICAL_PREDICATES: Set[str] = {p.value for p in CanonicalPredicate}

    DISALLOWED_GENERIC_VERBS: Set[str] = {
        "be", "is", "are", "defines", "specifies", "cover", "covers",
        "issue", "start", "verify", "override", "has_refund", "have", "has",
    }

    RAW_PHRASE_MAPPINGS = {
        "must verify each condition": CanonicalPredicate.MUST_VERIFY_REFUND_CONDITIONS.value,
        "must verify refund conditions": CanonicalPredicate.MUST_VERIFY_REFUND_CONDITIONS.value,
        "can start a return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "can start their return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "start return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "may override these terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "may override standard terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "override standard terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "requires manager approval": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "team lead approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "manager approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "director approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "fraud review required": CanonicalPredicate.REQUIRES_FRAUD_REVIEW.value,
        "secondary fraud review": CanonicalPredicate.REQUIRES_FRAUD_REVIEW.value,
        "can be cancelled": CanonicalPredicate.HAS_CANCELLATION_ELIGIBILITY.value,
        "can it be cancelled": CanonicalPredicate.HAS_CANCELLATION_ELIGIBILITY.value,
        "full refund within 3–5 days": CanonicalPredicate.HAS_CANCELLATION_REFUND_TIMING.value,
        "full refund within 3-5 days": CanonicalPredicate.HAS_CANCELLATION_REFUND_TIMING.value,
        "see section 9": CanonicalPredicate.HAS_INTERNAL_POLICY_REFERENCE.value,
        "see section 14": CanonicalPredicate.HAS_INTERNAL_POLICY_REFERENCE.value,
        "covered by warranty": CanonicalPredicate.HAS_RESOLUTION_PATH.value,
    }

    @classmethod
    def is_canonical(cls, predicate: str) -> bool:
        """Checks if a predicate is a valid approved canonical predicate."""
        if not predicate:
            return False
        return predicate.strip().lower() in cls.CANONICAL_PREDICATES

    @classmethod
    def is_disallowed_generic(cls, predicate: str) -> bool:
        """Checks if a predicate is a prohibited bare verb or generic token."""
        if not predicate:
            return True
        p_clean = predicate.strip().lower()
        return (
            p_clean in cls.DISALLOWED_GENERIC_VERBS
            or p_clean.isdigit()
            or len(p_clean) <= 1
        )

    @classmethod
    def normalize_predicate(cls, raw_pred: str) -> Tuple[str, bool]:
        """
        Normalizes a raw predicate verb phrase into an approved canonical predicate.
        Returns:
            (canonical_predicate, is_canonical)
        """
        if not raw_pred:
            return "", False

        cleaned = raw_pred.strip().lower()

        # 1. Direct registry hit
        if cleaned in cls.CANONICAL_PREDICATES:
            return cleaned, True

        # 2. Known raw phrase mapping
        if cleaned in cls.RAW_PHRASE_MAPPINGS:
            return cls.RAW_PHRASE_MAPPINGS[cleaned], True

        for phrase, mapped in cls.RAW_PHRASE_MAPPINGS.items():
            if phrase in cleaned:
                return mapped, True

        # 3. Disallowed generic token
        if cls.is_disallowed_generic(cleaned):
            return cleaned, False

        # 4. Unknown but syntactically valid predicate
        return cleaned, False
