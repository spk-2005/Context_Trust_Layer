"""
Enterprise Domain Facet Registry.

Provides structured, domain-specific facet definitions for enterprise governance,
HR, compliance, security, and contractual policies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class EnterpriseDomainFacet(str, Enum):
    NOTICE_PERIOD = "notice_period"
    LEAVE_ENTITLEMENTS = "leave_entitlements"
    COMPENSATION_DEDUCTIONS = "compensation_deductions"
    ASSET_MANAGEMENT = "asset_management"
    CONFIDENTIALITY_IP = "confidentiality_ip"
    SECURITY_ACCESS = "security_access"
    DATA_RETENTION = "data_retention"
    RETAIL_RETURNS = "return_window"
    SUPPORT_CHANNELS = "support_channels"
    PRODUCT_WARRANTY = "product_warranty"
    GENERAL = "general"


@dataclass
class DomainFacetDefinition:
    facet_name: EnterpriseDomainFacet
    description: str
    patterns: List[str]
    predicates: Set[str] = field(default_factory=set)
    condition_dimensions: Set[str] = field(default_factory=set)
    compatible_units: Set[str] = field(default_factory=set)


ENTERPRISE_FACET_REGISTRY: Dict[str, DomainFacetDefinition] = {
    "notice_period": DomainFacetDefinition(
        facet_name=EnterpriseDomainFacet.NOTICE_PERIOD,
        description="Employee notice durations, probation rules, and separation timeframes.",
        patterns=[
            r"\bnotice\s+period\b",
            r"\bnotice\s+duration\b",
            r"\bprobationers\b",
            r"\bprobationary\b",
            r"\bshort\s+notice\b",
            r"\bconfirmed\s+(?:employees|status)\b",
            r"\bgrade\s+[a-e]\b",
        ],
        predicates={
            "has_notice_duration",
            "has_probationary_notice_duration",
            "has_confirmed_notice_duration",
            "holds_right_to_recover_short_notice",
        },
        condition_dimensions={"employment_status", "service_tenure", "resignation_type"},
        compatible_units={"days", "weeks", "months"},
    ),
    "leave_entitlements": DomainFacetDefinition(
        facet_name=EnterpriseDomainFacet.LEAVE_ENTITLEMENTS,
        description="Annual leaves, sick leaves, notice period leave requests, and quotas.",
        patterns=[
            r"\bleave\s+during\s+notice\b",
            r"\bholiday\s+or\s+leave\b",
            r"\bexcess\s+leaves?\b",
            r"\ballotted\s+quota\b",
            r"\bannual\s+leave\b",
            r"\bparental\s+leave\b",
        ],
        predicates={"request_leave_during_notice_period", "recovered_beyond_quota"},
        condition_dimensions={"approval_required", "quota_exceeded"},
        compatible_units={"days", "hours"},
    ),
    "compensation_deductions": DomainFacetDefinition(
        facet_name=EnterpriseDomainFacet.COMPENSATION_DEDUCTIONS,
        description="Full & Final settlement adjustments, loans, bonuses, and tax deductions.",
        patterns=[
            r"\bfull\s+and\s+final\b",
            r"\bf&f\b",
            r"\bdeductions?\b",
            r"\bloans?\s+(?:and|&)\s+advances\b",
            r"\bwfh\s+allowance\b",
            r"\bjoining\s+bonus\b",
            r"\bepf\b",
            r"\bvpf\b",
            r"\btax\s+deductions?\b",
            r"\bstatutory\s+deductions\b",
        ],
        predicates={
            "deducted_per_asset_management_policy",
            "adjusted_from_full_and_final_salary",
            "recovered_upon_early_exit",
            "governed_by_offer_letter_terms",
            "made_and_deposited_into_account",
            "deducted_without_investment_proofs",
        },
        condition_dimensions={"exit_tenure", "asset_retained", "loan_outstanding"},
        compatible_units={"currency", "percentage", "amount", "inr", "usd"},
    ),
    "asset_management": DomainFacetDefinition(
        facet_name=EnterpriseDomainFacet.ASSET_MANAGEMENT,
        description="Company hardware, laptops, monitors, property return, and shipping.",
        patterns=[
            r"\bcompany\s+(?:laptop|assets?|property)\b",
            r"\bretention\b",
            r"\basset\s+management\b",
            r"\boffboarding\b",
            r"\breturn\s+all\s+wingify\b",
            r"\bshipping\s+costs?\b",
        ],
        predicates={"return", "cover", "deducted_per_asset_management_policy"},
        condition_dimensions={"lifecycle_phase"},
        compatible_units=set(),
    ),
    "confidentiality_ip": DomainFacetDefinition(
        facet_name=EnterpriseDomainFacet.CONFIDENTIALITY_IP,
        description="NDAs, intellectual property, document confidentiality, and disclosure prohibitions.",
        patterns=[
            r"\bconfidential\b",
            r"\bunauthorized\s+use\b",
            r"\bdisclosure\b",
            r"\breproduced?\b",
            r"\breproduction\b",
            r"\btrade\s+secrets?\b",
            r"\bconfidentiality\s+obligations\b",
        ],
        predicates={
            "prohibited_in_any_media",
            "prohibited_except_internal_confidential_use",
        },
        condition_dimensions={"purpose", "authorization"},
        compatible_units=set(),
    ),
}
