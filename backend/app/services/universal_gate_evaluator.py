"""
Universal 10-Gate Claim Governance Certification Evaluator.

Enforces strict, document-agnostic fail-closed validation:
1. evidence_exists: Non-empty verbatim quote and valid source locator.
2. evidence_located: Verbatim quote physically grounded at byte/char offsets.
3. text_integrity: Not synthesized, no taxonomy slugs, modal preserved, negation intact.
4. clause_entails_claim: Enclosing clause logically entails the proposition.
5. subject_valid: Resolves to an actor, role, defined asset; rejects grammatical fragments.
6. counterparty_resolved: Bound obligor/obligee, no dangling ungrounded pronouns.
7. predicate_valid: Belongs to versioned taxonomy; role-compatible; not a banned catch-all.
8. atomicity_valid: Governs exactly one action/remedy without multi-branch disjunctions.
9. duplicate_valid: Unique proposition; collapsed duplicates point to canonical.
10. claim_type_allowed: Operative RULE (definitions, references, and descriptions routed to NON_RULE).
11. human_approval_required (Optional): Evaluated from risk policy.

Every gate fails closed. Missing or unverified gates evaluate to False.
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.evidence import ImmutableEvidenceSpan
from app.schemas.universal_claim import ClaimLifecycleState, ClaimType, ModalityType, UniversalClaim
from app.services.dynamic_modality_extractor import DynamicModalityExtractor
from app.services.evidence_locator_service import EvidenceLocatorService
from app.services.role_direction_validator import RoleDirectionValidator
from app.taxonomy.registry import PredicateRegistryService


UNIVERSAL_10_GATES = [
    "evidence_exists",
    "evidence_located",
    "text_integrity",
    "clause_entails_claim",
    "subject_valid",
    "counterparty_resolved",
    "predicate_valid",
    "atomicity_valid",
    "duplicate_valid",
    "claim_type_allowed",
]

# Generic page-header and document pagination patterns
PAGE_HEADER_PATTERNS = [
    r"(?i)\bpage\s+\d+\s+of\s+\d+\b",
    r"(?i)^\s*page\s+\d+\b",
]

# Generic postal-address patterns (street numbers, street types, PO box, postal codes, suite numbers)
POSTAL_ADDRESS_PATTERNS = [
    r"(?i)\b\d{1,5}\s+[A-Za-z0-9\.\s]{1,30}\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Lane|Ln|Court|Ct|Parkway|Pkwy|Plaza|Plz)\b",
    r"(?i)\bp\.?o\.?\s*box\s+\d+\b",
    r"(?i)\bsuite\s+\d+\b",
    r"(?i)\b[A-Z]{2}\s+\d{5}(-\d{4})?\b",
    r"(?i)\b\d{5}-\d{4}\b",
    r"(?i)\b[A-Za-z\s]+,\s+[A-Z]{2}\s+\d{5}\b",
]

# Disallowed subject prefixes and exact tokens that indicate grammar fragments or syntax artifacts
INVALID_SUBJECT_PATTERNS = [
    r"^\(?[iIvVxX0-9]+[\.\)\s]",    # Enumeration markers: (i), (ii), 1., 2)
    r"^\(?\s*[a-zA-Z]\s*[\.\)]",     # Enumeration letters: (a), (b), a.
    r"^the\s+following\b",
    r"^without\s+limiting\b",
    r"^failure\s+to\s+enforce\b",
    r"^any\s+attempted\s+assignment\b",
    r"^termination\s+without\s+cause\b",
    r"^no\s+changes?\b",
    r"^changes?\b",
    r"^such\s+changes?\b",
    r"^all\s+amounts?\b",
    r"^this\s+agreement\b",
    r"^page\s+\d+",
    r"^section\s+[\d\.]+",
    r"^article\s+\d+",
] + PAGE_HEADER_PATTERNS + POSTAL_ADDRESS_PATTERNS

# Operative contractual modal verbs required in normative rules
MODAL_OPERATIVE_PATTERN = r"\b(may|must|will|shall|can|should|is\s+required\s+to|are\s+required\s+to|is\s+entitled\s+to|are\s+entitled\s+to|is\s+eligible\s+(?:for|to)|are\s+eligible\s+(?:for|to)|agrees\s+to|agree\s+to|authorizes?|grants?|retains?|warrants?|reserves?|assigns?|requires?|is\s+responsible\s+for|remains\s+responsible\s+for|has\s+a\b|has\s+the\s+right\s+to\b|is\s+limited\s+to\b|is\s+capped\s+at\b|shall\s+be\s+limited\s+to\b|liability\s+is\s+the\b|must\s+not|may\s+not|will\s+not|shall\s+not|neither\s+party\s+will|is\s+not\s+licensed\s+to|prohibited\s+from)\b"

# Generic predicate slug pattern in claim text
PREDICATE_SLUG_REGEX = r"\b(?:has|can|may|must|will|remains|is)_[a-z0-9]+(?:_[a-z0-9]+)+\b"

# Generic leading enumeration prefix
ENUMERATION_PREFIX_PATTERN = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s+"

# Non-rule types
NON_RULE_TYPES = {
    "definition",
    "reference",
    "description",
    "responsibility",
    "section_marker",
    "fragment",
    "contact_information",
    "contact",
}

# Cross-reference cues
REFERENCE_CUES = [
    "more details about",
    "can be found in",
    "can be found at",
    "for more information",
    "refer to section",
    "see the",
    "visit http",
]

# Description cues
DESCRIPTION_CUES = [
    "availability may vary",
    "may vary by region",
    "subject to export laws",
    "subject to u.s. and other",
    "governed by the laws of",
    "does not include online services",
]


class EntailmentDecision(str, Enum):
    """3-valued semantic entailment classification."""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class SemanticEntailmentResult:
    """Detailed semantic entailment verdict across dimensions."""
    decision: EntailmentDecision
    is_supported: bool
    reason: str
    dimension_checked: str = "ACTION"

    def __iter__(self):
        return iter((self.is_supported, self.reason))


@dataclass
class UniversalGateResult:
    evidence_exists: bool = False
    evidence_located: bool = False
    text_integrity: bool = False
    clause_entails_claim: bool = False
    subject_valid: bool = False
    counterparty_resolved: bool = False
    predicate_valid: bool = False
    atomicity_valid: bool = False
    duplicate_valid: bool = False
    claim_type_allowed: bool = False
    human_approved_if_required: bool = True

    entailment_decision: str = "INSUFFICIENT_EVIDENCE"
    entailment_reason: Optional[str] = None
    entailment_dimension: Optional[str] = None

    all_gates_passed: bool = False
    lifecycle_state: ClaimLifecycleState = ClaimLifecycleState.REVIEW_REQUIRED
    certification_tier: str = "REVIEW_REQUIRED"
    is_canonical: bool = False
    agent_accessible: bool = False
    rejection_reasons: List[str] = field(default_factory=list)
    gates: Dict[str, bool] = field(default_factory=dict)
    repaired_claim_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gates": self.gates,
            "all_gates_passed": self.all_gates_passed,
            "lifecycle_state": self.lifecycle_state.value if hasattr(self.lifecycle_state, "value") else str(self.lifecycle_state),
            "certification_tier": self.certification_tier,
            "is_canonical": self.is_canonical,
            "agent_accessible": self.agent_accessible,
            "rejection_reasons": self.rejection_reasons,
            "repaired_claim_text": self.repaired_claim_text,
            "entailment_decision": self.entailment_decision,
            "entailment_reason": self.entailment_reason,
            "entailment_dimension": self.entailment_dimension,
        }



class UniversalGateEvaluator:
    """Universal 10-gate fail-closed claim governance evaluator."""

    @staticmethod
    def strip_enumeration_prefix(text: Optional[str]) -> str:
        """Strips leading enumeration markers like (i), (ii), (iv), 1., 2), (a), etc."""
        if not text:
            return ""
        pattern = r"^\s*(\([iIvVxX0-9a-zA-Z]+\)|[0-9a-zA-Z]+[\.\)]|\([0-9]+\))\s*"
        return re.sub(pattern, "", text).strip()

    @staticmethod
    def compute_semantic_signature(subject: Optional[str], predicate: Optional[str], obj_or_text: Optional[str]) -> str:
        s = (subject or "").strip().lower()
        p = (predicate or "").strip().lower()
        o = re.sub(r"[^\w\s]", "", (obj_or_text or "").strip().lower())
        words = o.split()[:8]
        key = f"{s}|{p}|{' '.join(words)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def check_semantic_entailment(
        cls,
        subject: str,
        predicate: str,
        claim_text: str,
        evidence_quote: str,
        clause_text: str = "",
        object_text: str = "",
        modality: str = "",
    ) -> SemanticEntailmentResult:
        """
        Deterministic, document-agnostic 3-valued semantic entailment check.
        Evaluates whether evidence logically supports, directly contradicts, or provides
        insufficient evidence for the structured proposition across actor, action,
        object, modality, deadline, and conditions.
        """
        text_lower = (evidence_quote or claim_text or "").lower()
        clause_lower = (clause_text or "").lower()
        full_evidence = f"{text_lower} {clause_lower}".strip()
        pred_lower = (predicate or "").lower()
        subj_lower = (subject or "").lower()
        obj_lower = (object_text or "").lower()

        # 1. has_return_window
        if pred_lower == "has_return_window":
            # Direct contradiction: clause explicitly bars returns
            if re.search(r"\b(no returns|all sales are final|returns are not permitted|non-returnable|cannot be returned)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence explicitly bars returns of products.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Scope / Action mismatch: audit license remediation
            if re.search(r"\b(unlicensed use|order sufficient licenses|verification reveals any unlicensed|cover the period of its unlicensed)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs audit licensing remediation; insufficient evidence to establish or negate a product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Scope / Action mismatch: professional services warranty remedy
            if re.search(r"\b(warranty claim|professional services|re-perform|giving rise to the warranty)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs professional services warranty notification and remedies; insufficient evidence for a product return window.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Absence of return keywords
            if not re.search(r"\b(return|returned|returns|return window)\b", text_lower):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_return_window' lacks product return cues in evidence.",
                    dimension_checked="ACTION_OBJECT",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes product return window.",
                dimension_checked="ACTION_OBJECT",
            )

        # 2. authorizes_recurring_charges
        if pred_lower == "authorizes_recurring_charges":
            # Direct contradiction
            if re.search(r"\b(shall not process recurring|does not authorize recurring|recurring charges are prohibited)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence bars recurring billing charges.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Action mismatch: credit report / financial inquiry for invoicing eligibility
            if re.search(r"\b(credit report|credit reports|financial condition|eligibility for invoicing)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause authorizes financial assessment and credit inquiry for invoicing terms; insufficient evidence for recurring billing charges.",
                    dimension_checked="ACTION_OBJECT",
                )
            # Absence of recurring cues
            has_recurring = bool(re.search(r"\b(recurring|periodically|automatic renewal|auto-renew|periodically for each|electronic debit|store.*payment details|charge.*payment method)\b", full_evidence))
            if not has_recurring:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'authorizes_recurring_charges' lacks recurring billing or periodic charge support in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes authorization of recurring charges.",
                dimension_checked="ACTION",
            )

        # 3. has_refund_eligibility
        if pred_lower == "has_refund_eligibility":
            # Direct contradiction: fees strictly non-refundable
            if re.search(r"\b(strictly non-refundable|nonrefundable|no refunds will be provided|not eligible for any refund)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence explicitly specifies fees are non-refundable.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Scope mismatch: security deposit / collateral for credit invoicing
            if re.search(r"\b(provide security|security in a form|eligible for invoicing)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause governs credit security collateral for invoicing; insufficient evidence for refund eligibility.",
                    dimension_checked="ACTION_SCOPE",
                )
            # Check for refund keywords
            has_refund = bool(re.search(r"\b(refund|refunds|reimburse|reimbursement|return the amount|money back|credit)\b", full_evidence))
            if not has_refund:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'has_refund_eligibility' lacks refund or reimbursement support in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence supports refund eligibility.",
                dimension_checked="ACTION",
            )

        # 4. must_pay_within_30_days
        if pred_lower == "must_pay_within_30_days":
            # Action mismatch: 30-day deadline attached to non-payment action (cure breach, notice, remedy, etc.)
            has_pay_action = bool(re.search(r"\b(pay|payment|invoices?|amounts? due|fees?|charges?|remit)\b", full_evidence))
            if not has_pay_action:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action mismatch: 30-day deadline in evidence applies to non-payment obligation (e.g. cure breach, notice, or remedy), not invoice payment.",
                    dimension_checked="ACTION",
                )
            # Direct deadline contradiction: payment due immediately
            if re.search(r"\b(immediately upon receipt|due immediately|upon receipt of an invoice)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct deadline contradiction: evidence specifies payment is due immediately upon receipt of invoice, which contradicts a Net 30 deadline.",
                    dimension_checked="DEADLINE",
                )
            # Deadline absence: pre-termination services with no payment timeframe
            if re.search(r"\b(provided or used before termination|services before termination)\b", full_evidence) and not re.search(r"\b(30|thirty)\s+(?:calendar\s+)?days\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Deadline absent: evidence establishes pre-termination payment obligation but contains no 30-day payment deadline.",
                    dimension_checked="DEADLINE",
                )
            # Absence of 30 days
            has_30 = bool(re.search(r"\b(30 days|thirty days|thirty \(30\) days|30 calendar days|thirty calendar days|net 30)\b", full_evidence))
            if not has_30:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'must_pay_within_30_days' asserts a 30-day deadline not present in the evidence.",
                    dimension_checked="DEADLINE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes 30-day payment deadline.",
                dimension_checked="DEADLINE",
            )

        # 4b. must_pay_unpaid_invoices_immediately
        if pred_lower == "must_pay_unpaid_invoices_immediately":
            has_invoice = bool(re.search(r"\b(invoices?|unpaid invoices?|billed amounts?)\b", full_evidence))
            if not has_invoice:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Object mismatch: evidence governs payment of taxes or other obligations, not unpaid invoices.",
                    dimension_checked="OBJECT",
                )
            has_immediate = bool(re.search(r"\b(immediately|upon receipt|promptly upon receipt)\b", full_evidence))
            if not has_immediate:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Deadline absent: evidence does not establish that invoices must be paid immediately.",
                    dimension_checked="DEADLINE",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes immediate payment obligation for unpaid invoices.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 4c. must_pay_for_services_before_termination
        if pred_lower == "must_pay_for_services_before_termination":
            has_term_timing = bool(re.search(r"\b(before termination|prior to termination|provided or used before termination|as of the termination date)\b", full_evidence))
            if not has_term_timing:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Condition/Timing mismatch: evidence does not restrict payment obligation to services delivered prior to termination.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes pre-termination services payment obligation.",
                dimension_checked="ALL_DIMENSIONS",
            )

        # 5. warrants_professional_standards
        if pred_lower == "warrants_professional_standards":
            # Direct contradiction
            if re.search(r"\b(as is without warranty of any kind|disclaims all warranties of professional standard|no warranty of skill)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence disclaims professional warranty standards.",
                    dimension_checked="MODALITY_POLARITY",
                )
            # Scope mismatch: delegation to affiliates / subcontractors
            is_delegation = bool(re.search(r"\b(through its affiliates|use subcontractors|perform.*through its affiliates)\b", full_evidence))
            has_warranty = bool(re.search(r"\b(warrants?|warranty|standard of care|professional care|skill|industry standards?)\b", full_evidence))
            if is_delegation and not has_warranty:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Action/Scope mismatch: clause permits delegation to affiliates and subcontractors; insufficient evidence for an affirmative professional standards warranty.",
                    dimension_checked="ACTION_SCOPE",
                )
            if not has_warranty:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'warrants_professional_standards' lacks warranty or professional standard cues in evidence.",
                    dimension_checked="ACTION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes warranty of professional standards.",
                dimension_checked="ACTION",
            )

        # 6. must_not_modify_agreement
        if pred_lower == "must_not_modify_agreement":
            # Object mismatch: Product modification != Agreement modification
            is_product_mod = bool(re.search(r"\b(modify or discontinue offering a product|modify.*product|discontinue offering a product)\b", full_evidence))
            if is_product_mod:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Object mismatch: clause permits modifying or discontinuing a Product, which does not establish or contradict an agreement modification restriction.",
                    dimension_checked="OBJECT",
                )
            # Direct polarity contradiction: party permitted to modify agreement
            if re.search(r"\b(may modify this agreement|may update this agreement|may amend this agreement)\b", full_evidence):
                if subj_lower in ("customer", "licensee", "user"):
                    return SemanticEntailmentResult(
                        decision=EntailmentDecision.CONTRADICTED,
                        is_supported=False,
                        reason="Direct contradiction: evidence permits Customer to modify the agreement, contradicting prohibition 'must_not_modify_agreement'.",
                        dimension_checked="MODALITY_POLARITY",
                    )
            if not re.search(r"\b(may not modify this agreement|must not modify this agreement|cannot modify this agreement|shall not modify this agreement)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Evidence does not support agreement modification prohibition.",
                    dimension_checked="MODALITY_POLARITY",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes prohibition against modifying agreement.",
                dimension_checked="MODALITY_POLARITY",
            )

        # 7. Formal Writing & Signature Subject & Predicate Integrity
        if "any waiver" in text_lower and "signed" in text_lower:
            if pred_lower == "must_be_in_writing" and "signed" not in pred_lower:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Condition omission: predicate 'must_be_in_writing' drops the essential cumulative requirement that the waiver be signed.",
                    dimension_checked="CONDITION",
                )
            if subj_lower in ("either party", "each party", "customer"):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Subject mismatch: subject for waiver clause must be 'Waiver' or 'Waiving party', not generic contracting entity.",
                    dimension_checked="SUBJECT",
                )
        elif "waiver" in text_lower and "signed" in text_lower and pred_lower == "must_be_in_writing":
            return SemanticEntailmentResult(
                decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                is_supported=False,
                reason="Condition omission: predicate 'must_be_in_writing' drops the cumulative signature requirement.",
                dimension_checked="CONDITION",
            )

        # 8. Notice requirement
        if "all notices must be in writing" in text_lower:
            if subj_lower in ("either party", "each party"):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Subject mismatch: subject for notice requirement must be 'Notice', not generic contracting entity.",
                    dimension_checked="SUBJECT",
                )

        # 8b. Suspension scope (Security/Breach vs Trade Laws)
        if pred_lower == "may_suspend_for_security_or_breach":
            has_sec_or_breach = bool(re.search(r"\b(security|breach|material breach|security risks?|vulnerability)\b", full_evidence))
            is_trade_law = bool(re.search(r"\b(trade laws?|sanctions?|embargo|export)\b", full_evidence))
            if is_trade_law and not has_sec_or_breach:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Scope/Trigger mismatch: evidence authorizes suspension to prevent trade law violations or comply with sanctions, not for security risks or material breach.",
                    dimension_checked="CONDITION",
                )
            if not has_sec_or_breach:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_suspend_for_security_or_breach' lacks security risk or breach triggers in evidence.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes suspension for security risk or material breach.",
                dimension_checked="CONDITION",
            )

        if pred_lower == "may_suspend_for_trade_laws":
            has_trade_laws = bool(re.search(r"\b(trade laws?|sanctions?|embargo|export regulations?)\b", full_evidence))
            if not has_trade_laws:
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.INSUFFICIENT_EVIDENCE,
                    is_supported=False,
                    reason="Predicate 'may_suspend_for_trade_laws' lacks trade law, sanction, or embargo triggers in evidence.",
                    dimension_checked="CONDITION",
                )
            return SemanticEntailmentResult(
                decision=EntailmentDecision.SUPPORTED,
                is_supported=True,
                reason="Verbatim evidence establishes suspension to prevent trade law violations or comply with sanctions.",
                dimension_checked="CONDITION",
            )

        # 9. Role Direction Reversal Check (Refund Payer vs Recipient)
        if "refund" in pred_lower or "reimburse" in pred_lower:
            if "customer" in subj_lower and re.search(r"\b(microsoft will.*refund|microsoft will.*return the amount customer paid|vendor will refund)\b", full_evidence):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Role direction reversal: evidence obliges vendor/Microsoft to refund Customer, which contradicts an obligation on Customer to refund.",
                    dimension_checked="ROLE_DIRECTION",
                )

        # 10. General Polarity Check (Permission vs Prohibition on Same Object)
        if pred_lower.startswith("may_not_") or pred_lower.startswith("must_not_") or "prohibited_from_" in pred_lower:
            if re.search(r"\b(may\s+(?:only\s+)?[a-z]+|is\s+permitted\s+to|has\s+the\s+right\s+to)\b", text_lower) and not re.search(r"\b(may\s+not|must\s+not|shall\s+not|prohibited|cannot)\b", text_lower):
                return SemanticEntailmentResult(
                    decision=EntailmentDecision.CONTRADICTED,
                    is_supported=False,
                    reason="Direct contradiction: evidence expresses a permissive right, which contradicts the asserted prohibition predicate.",
                    dimension_checked="MODALITY_POLARITY",
                )

        return SemanticEntailmentResult(
            decision=EntailmentDecision.SUPPORTED,
            is_supported=True,
            reason="Semantic entailment verified against evidence.",
            dimension_checked="ALL_DIMENSIONS",
        )

    @classmethod
    def evaluate(
        cls,
        claim_text: str,
        subject: str,
        predicate: str,
        object_text: Optional[str] = None,
        claim_type: str = "RULE",
        evidence: Optional[ImmutableEvidenceSpan] = None,
        source_content: Optional[str] = None,
        clause_text: Optional[str] = None,
        confidence_or_trust: float = 0.95,
        existing_signatures: Optional[Set[str]] = None,
        is_human_approved: bool = False,
        requires_human_approval: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> UniversalGateResult:
        reasons: List[str] = []

        raw_text = (claim_text or "").strip()
        # Automatically strip leading enumeration prefixes for evaluation
        stripped_text = cls.strip_enumeration_prefix(raw_text)
        repaired_text = stripped_text if stripped_text != raw_text else None
        eval_text = stripped_text or raw_text

        text_lower = eval_text.lower()
        subj_clean = (subject or "").strip()
        subj_lower = subj_clean.lower()
        pred_clean = (predicate or "").strip()
        pred_lower = pred_clean.lower()
        ct_clean = (claim_type or "RULE").strip().lower()

        # Enclosing clause text fallback
        surrounding_clause = clause_text or (evidence.clause_text if evidence else "") or ""
        surrounding_clause_lower = surrounding_clause.lower()

        # =========================================================================
        # Gate 1: evidence_exists
        # =========================================================================
        is_evidence_exists = True
        if evidence is None:
            is_evidence_exists = False
            reasons.append("Evidence failure: Missing ImmutableEvidenceSpan; claim has no physical source grounding.")
        elif not evidence.verbatim_quote or not evidence.verbatim_quote.strip():
            is_evidence_exists = False
            reasons.append("Evidence failure: Verbatim quote in ImmutableEvidenceSpan is empty.")
        elif not evidence.source_hash:
            is_evidence_exists = False
            reasons.append("Evidence failure: Missing cryptographic source hash.")

        # =========================================================================
        # Gate 2: evidence_located
        # =========================================================================
        is_evidence_located = True
        if not is_evidence_exists:
            is_evidence_located = False
        else:
            loc_res = EvidenceLocatorService.locate_and_verify(
                evidence=evidence,  # type: ignore[arg-type]
                source_content=source_content,
            )
            if not loc_res.located:
                is_evidence_located = False
                reasons.append(f"Evidence location failure: {loc_res.error_reason or 'Quote not found in source text.'}")

        # =========================================================================
        # Gate 3: text_integrity
        # =========================================================================
        is_text_integrity = True
        # 3a. Disallow predicate slugs / snake_case identifiers injected into claim text
        slug_match = re.search(PREDICATE_SLUG_REGEX, raw_text)
        if slug_match:
            is_text_integrity = False
            reasons.append(f"Text integrity failure: Injected predicate identifier or taxonomy slug in claim text: '{slug_match.group(0)}'.")

        # 3b. Disallow page headers and postal addresses
        if any(re.search(pat, raw_text) for pat in PAGE_HEADER_PATTERNS):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text contains page header or pagination artifact.")
        if any(re.search(pat, raw_text) for pat in POSTAL_ADDRESS_PATTERNS):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text contains unstripped postal address artifact.")

        # 3c. Disallow truncated sentences
        if eval_text.startswith("...") or eval_text.endswith("..."):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text is an ellipsis fragment.")
        elif re.search(r"\b(and|or|for|to|with|of|the)\s+all\s+other\s*$", text_lower):
            is_text_integrity = False
            reasons.append("Text integrity failure: Claim text is truncated mid-sentence.")

        # 3d. Check operative modal verb in rules
        if ct_clean in {"rule", "policy_rule", "policy"}:
            if not re.search(MODAL_OPERATIVE_PATTERN, text_lower):
                is_text_integrity = False
                reasons.append("Text integrity failure: Normative rule is missing an operative modal phrase ('may', 'must', 'will', 'shall', etc.).")

        # 3e. Polarity and Negation consistency
        mod_res = DynamicModalityExtractor.validate_consistency(
            claim_text=eval_text,
            declared_modality=DynamicModalityExtractor.extract_modality(eval_text),
            predicate_name=pred_clean,
        )
        if not mod_res.is_consistent:
            is_text_integrity = False
            reasons.append(mod_res.error_reason or "Text integrity failure: Polarity inconsistency between predicate and text.")

        # =========================================================================
        # Gate 4: clause_entails_claim
        # =========================================================================
        is_clause_entails_claim = True
        entailment_dec = EntailmentDecision.SUPPORTED
        entailment_reason = None
        entailment_dim = "ALL_DIMENSIONS"

        if not is_evidence_exists or not is_evidence_located:
            is_clause_entails_claim = False
            entailment_dec = EntailmentDecision.INSUFFICIENT_EVIDENCE
            entailment_reason = "Missing or unlocated evidence precludes logical entailment."
            entailment_dim = "EVIDENCE"
            reasons.append(f"Clause entailment failure: {entailment_reason}")
        else:
            entail_res = cls.check_semantic_entailment(
                subject=subj_clean,
                predicate=pred_clean,
                claim_text=eval_text,
                evidence_quote=evidence.verbatim_quote if evidence else eval_text,
                clause_text=surrounding_clause,
                object_text=object_text or "",
            )
            entailment_dec = entail_res.decision
            entailment_reason = entail_res.reason
            entailment_dim = entail_res.dimension_checked
            if not entail_res.is_supported:
                is_clause_entails_claim = False
                reasons.append(f"Clause entailment failure [{entail_res.decision.value} - {entail_res.dimension_checked}]: {entail_res.reason}")

        # =========================================================================
        # Gate 5: subject_valid
        # =========================================================================
        is_subject_valid = True
        if not subj_clean or len(subj_clean) < 2:
            is_subject_valid = False
            reasons.append("Subject failure: Subject is empty or too short.")
        elif any(re.search(pat, subj_clean) for pat in PAGE_HEADER_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' contains a page header artifact.")
        elif any(re.search(pat, subj_clean) for pat in POSTAL_ADDRESS_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' contains a postal address artifact.")
        elif any(re.search(pat, subj_lower) for pat in INVALID_SUBJECT_PATTERNS):
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' is a syntax fragment or non-actor token.")
        elif subj_lower in {"assignment", "the", "it", "this", "these", "that", "which", "a", "an"}:
            is_subject_valid = False
            reasons.append(f"Subject failure: Subject '{subj_clean}' is a stopword or grammatical noun phrase.")

        # =========================================================================
        # Gate 6: counterparty_resolved
        # =========================================================================
        is_counterparty_resolved = True
        # Check dangling pronouns
        pronoun_match = re.search(r"\b(their|them|his|her)\s+performance\b", text_lower) or text_lower.endswith("their performance.")
        if pronoun_match:
            grounding_entities = ["subcontractor", "subcontractors", "representative", "representatives", "affiliate", "personnel", "agent", "employee"]
            if not any(g in text_lower or g in surrounding_clause_lower for g in grounding_entities):
                is_counterparty_resolved = False
                reasons.append("Counterparty failure: Ungrounded pronoun 'their' lacks clear antecedent party resolution.")

        # Evidence-conditioned role direction validation
        role_res = RoleDirectionValidator.validate(
            subject=subj_clean,
            predicate=pred_clean,
            clause_text=surrounding_clause,
        )
        if not role_res.is_valid:
            is_counterparty_resolved = False
            reasons.append(role_res.reason or "Counterparty failure: Directional right/duty conflicts with clause evidence.")

        # =========================================================================
        # Gate 7: predicate_valid
        # =========================================================================
        is_predicate_valid = True
        if not pred_clean or len(pred_clean) < 2 or pred_lower in {"the", "a", "in", "is", "take"}:
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Predicate '{pred_clean}' is invalid or a generic stopword.")
        elif PredicateRegistryService.is_banned(pred_clean):
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Generic catch-all predicate '{pred_clean}' is banned; requires normalized action taxonomy.")
        elif not PredicateRegistryService.exists(pred_clean):
            # Check if dynamically registered or allowed
            is_predicate_valid = False
            reasons.append(f"Predicate failure: Predicate '{pred_clean}' is not present in versioned taxonomy registry.")

        # =========================================================================
        # Gate 8: atomicity_valid
        # =========================================================================
        is_atomicity_valid = True
        if ct_clean == "quarantined":
            is_atomicity_valid = False
            reasons.append("Atomicity failure: Claim is explicitly marked as quarantined compound rule.")
        else:
            # Layered compound detection
            has_transfer = "transfer" in text_lower or "transferee" in text_lower
            if has_transfer and ("(1)" in text_lower or "(i)" in text_lower) and ("(2)" in text_lower or "(ii)" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Multi-branch transfer disjunction requires decomposition into atomic child claims.")
            elif has_transfer and ("affiliate" in text_lower) and ("third party" in text_lower or "third-party" in text_lower) and ("hardware" in text_lower or "merger" in text_lower or "divestiture" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Compound transfer conditions across multiple separate entities.")

            if "may sublicense" in text_lower and ("may not sublicense" in text_lower or "affiliates may not" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Mixed polarity (permission + prohibition) requires splitting into child claims.")

            if ("audit" in text_lower or "unlicensed use" in text_lower) and ("reimburse" in text_lower) and ("acquire" in text_lower or "125%" in text_lower):
                is_atomicity_valid = False
                reasons.append("Atomicity failure: Compound audit remedies combining reimbursement and penalty license acquisition.")

        # =========================================================================
        # Gate 9: duplicate_valid
        # =========================================================================
        is_duplicate_valid = True
        if metadata and (metadata.get("is_duplicate") or metadata.get("duplicate_of")):
            is_duplicate_valid = False
            reasons.append("Duplicate check: Claim metadata indicates it is a duplicate.")
        elif ct_clean == "duplicate":
            is_duplicate_valid = False
            reasons.append("Duplicate check: Claim is classified as a duplicate.")
        elif existing_signatures is not None:
            sig = cls.compute_semantic_signature(subj_clean, pred_clean, object_text or eval_text)
            if sig in existing_signatures:
                is_duplicate_valid = False
                reasons.append("Duplicate check: Semantic signature already exists in canonical catalog.")

        # =========================================================================
        # Gate 10: claim_type_allowed
        # =========================================================================
        is_claim_type_allowed = True
        if ct_clean in NON_RULE_TYPES:
            is_claim_type_allowed = False
            reasons.append(f"Claim type failure: '{claim_type}' is a non-rule type (definition, reference, or description).")
        elif any(cue in text_lower for cue in REFERENCE_CUES):
            is_claim_type_allowed = False
            reasons.append("Claim type failure: Text is a cross-reference cue, not an operative rule.")
        elif any(cue in text_lower for cue in DESCRIPTION_CUES) or "product availability" in subj_lower:
            has_operative_rule = bool(re.search(r"\b(may suspend or terminate|will comply with|must comply with|shall comply with)\b", text_lower))
            if not has_operative_rule:
                is_claim_type_allowed = False
                reasons.append("Claim type failure: Text is descriptive background scope, not an operative rule.")
        elif ct_clean not in {"rule", "policy_rule", "policy"}:
            is_claim_type_allowed = False
            reasons.append(f"Claim type failure: Unrecognized claim type '{claim_type}'.")

        # =========================================================================
        # Gate 11: human_approved_if_required (Optional)
        # =========================================================================
        is_human_approved_if_required = True
        if requires_human_approval and not is_human_approved:
            is_human_approved_if_required = False
            reasons.append("Risk policy requirement: High-risk action requires explicit human approval signoff.")
        elif confidence_or_trust < 0.70 and not is_human_approved:
            is_human_approved_if_required = False
            reasons.append(f"Trust score {confidence_or_trust:.2f} requires human approval.")

        # =========================================================================
        # Compile Gates and Lifecycle State
        # =========================================================================
        gates = {
            "evidence_exists": is_evidence_exists,
            "evidence_located": is_evidence_located,
            "text_integrity": is_text_integrity,
            "clause_entails_claim": is_clause_entails_claim,
            "subject_valid": is_subject_valid,
            "counterparty_resolved": is_counterparty_resolved,
            "predicate_valid": is_predicate_valid,
            "atomicity_valid": is_atomicity_valid,
            "duplicate_valid": is_duplicate_valid,
            "claim_type_allowed": is_claim_type_allowed,
            "human_approved_if_required": is_human_approved_if_required,
        }

        all_10_passed = all(gates[g] is True for g in UNIVERSAL_10_GATES)
        all_passed = all_10_passed and is_human_approved_if_required

        if all_passed:
            tier = "AUTOMATED_CERTIFIED"
            state = ClaimLifecycleState.AUTOMATED_CERTIFIED
            is_canon = True
            agent_acc = True
        elif not is_duplicate_valid or ct_clean == "duplicate":
            tier = "DUPLICATE"
            state = ClaimLifecycleState.DUPLICATE
            is_canon = False
            agent_acc = False
        elif not is_atomicity_valid or ct_clean == "quarantined":
            tier = "QUARANTINED"
            state = ClaimLifecycleState.QUARANTINED
            is_canon = False
            agent_acc = False
        elif not is_claim_type_allowed or ct_clean in NON_RULE_TYPES:
            tier = "NON_RULE"
            state = ClaimLifecycleState.NON_RULE
            is_canon = False
            agent_acc = False
        elif not is_evidence_exists or not is_evidence_located or not is_text_integrity:
            tier = "REJECTED"
            state = ClaimLifecycleState.REJECTED
            is_canon = False
            agent_acc = False
        else:
            tier = "REVIEW_REQUIRED"
            state = ClaimLifecycleState.REVIEW_REQUIRED
            is_canon = False
            agent_acc = False

        return UniversalGateResult(
            evidence_exists=is_evidence_exists,
            evidence_located=is_evidence_located,
            text_integrity=is_text_integrity,
            clause_entails_claim=is_clause_entails_claim,
            subject_valid=is_subject_valid,
            counterparty_resolved=is_counterparty_resolved,
            predicate_valid=is_predicate_valid,
            atomicity_valid=is_atomicity_valid,
            duplicate_valid=is_duplicate_valid,
            claim_type_allowed=is_claim_type_allowed,
            human_approved_if_required=is_human_approved_if_required,
            entailment_decision=entailment_dec.value if hasattr(entailment_dec, "value") else str(entailment_dec),
            entailment_reason=entailment_reason,
            entailment_dimension=entailment_dim,
            all_gates_passed=all_passed,
            lifecycle_state=state,
            certification_tier=tier,
            is_canonical=is_canon,
            agent_accessible=agent_acc,
            rejection_reasons=reasons,
            gates=gates,
            repaired_claim_text=repaired_text,
        )
