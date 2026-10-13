"""
Layer 5: Domain Rules Extractor.
Extracts structured claims from normative policy clauses, compliance rules, and conversational decisions
using deterministic grammar patterns, modal logic parsing, and domain heuristics.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.extraction.subject_normalizer import SubjectNormalizer
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


class DomainRuleExtractor:
    """Grammar and modal pattern extractor for policy clauses and standard requirements."""

    CONDITIONAL_SPLIT_REGEX = re.compile(
        r"^(?:if|in cases where|in the event that|where)\s+(?P<condition>.*?),\s+(?P<main_clause>.*)$",
        re.IGNORECASE,
    )
    MODAL_SPLIT_REGEX = re.compile(
        r"^(?P<subject>.*?)\s+\b(?P<modal>must|shall|is required to|are required to|prohibited from|cannot|can not|should|will|is mandatory for|are mandatory for|holds the right to|reserves the right to|is permitted to|are permitted to|may|can)\s+(?P<predicate_object>.*)$",
        re.IGNORECASE,
    )

    NON_CANONICAL_ROLES = (
        ContentRole.EXAMPLE,
        ContentRole.REVISION_HISTORY,
        ContentRole.CONTACT_INFO,
        ContentRole.FAQ,
        ContentRole.FAQ_QUESTION,
        ContentRole.FAQ_ANSWER,
        ContentRole.DEFINITION,
        ContentRole.HEADING,
        ContentRole.INTRODUCTORY_CONTEXT,
        ContentRole.DOCUMENT_METADATA,
        ContentRole.FORM_SPECIFICATION,
    )

    PROTECTED_ABBREVIATIONS = (
        r"\b(?:e\.g\.|i\.e\.|etc\.|vs\.|al\.|u\.s\.|u\.k\.|fig\.|sec\.|no\.)",
        r"\b(?:e\.g|i\.e)\.\s*",
        r"\b\d+\.\d+\b",
    )

    @classmethod
    def split_sentences_safely(cls, text: str) -> List[str]:
        """Splits narrative text into sentences without fragmenting protected abbreviations (e.g., i.e.)."""
        if not text:
            return []

        def _mask(m):
            return m.group(0).replace(".", "__DOT__")

        protected = text
        for pat in cls.PROTECTED_ABBREVIATIONS:
            protected = re.sub(pat, _mask, protected, flags=re.IGNORECASE)

        splits = [s.strip() for s in re.split(r"(?<=[.!?])\s+", protected) if s.strip()]
        sentences = [s.replace("__DOT__", ".") for s in splits if s]
        return sentences or [text]

    @classmethod
    def normalize_predicate_and_modality(
        cls, raw_pred: str, raw_pred_obj: str, clean_sentence: str, raw_modal: str, current_modality: str
    ) -> Tuple[str, str, str]:
        """
        Maps weak raw verbs and sentence-copied predicates into enterprise-grade canonical predicates.
        Returns (canonical_predicate, refined_object, refined_modality).
        """
        raw_p = raw_pred.lower().strip()
        obj_lower = raw_pred_obj.lower().strip()
        sent_lower = clean_sentence.lower().strip()
        modality = current_modality

        # 1. Override terms (e.g. Business customers may override standard terms)
        if "override" in raw_p or "override" in obj_lower:
            return "may_override_standard_terms", raw_pred_obj, "PERMISSION"

        # 2. Initiate / Start return (e.g. Customers can start their return online)
        if raw_p in ("start", "initiate", "begin") and any(w in obj_lower or w in sent_lower for w in ("return", "refund", "process", "request")):
            return "can_initiate_return", raw_pred_obj, "PERMISSION"

        # 3. Verification & Fraud (e.g. must verify refund conditions, secondary fraud review)
        if raw_p in ("verify", "validate", "check", "inspect"):
            if "fraud" in obj_lower or "fraud" in sent_lower:
                return "requires_fraud_review", raw_pred_obj, "OBLIGATION"
            return "must_verify_refund_conditions", raw_pred_obj, "OBLIGATION"

        # 4. Return windows & condition (e.g. Items must be returned within 30 days)
        if raw_p in ("be", "is", "are"):
            if any(k in obj_lower for k in ("initiated within", "within the applicable", "applicable return window")):
                return "requires_return_within_applicable_window", raw_pred_obj, "OBLIGATION"
            if any(k in obj_lower for k in ("returned within", "return within", "window", "within 30 days", "within 14 days", "within 60 days")):
                return "has_return_window", raw_pred_obj, "OBLIGATION"
            if any(k in obj_lower for k in ("deadline", "until january", "until december", "by january", "by december")):
                return "has_return_deadline", raw_pred_obj, "OBLIGATION"
            if any(k in obj_lower for k in ("original condition", "undamaged", "unworn", "tags intact", "packaging intact")):
                return "must_be_in_original_condition", raw_pred_obj, "OBLIGATION"
            if "eligible" in obj_lower:
                return "has_refund_eligibility", raw_pred_obj, "POLICY_FACT"
            if any(w in sent_lower for w in ("receipt", "proof of purchase", "order number")) and any(w in obj_lower for w in ("provided", "provide", "submitted", "submit", "present")):
                return "requires_verifiable_order_or_purchase_proof", raw_pred_obj, "OBLIGATION"
            return "must_satisfy_requirement", raw_pred_obj, modality

        # 5. Definitions
        if raw_p in ("defines", "defined"):
            return "has_definition", raw_pred_obj, "POLICY_FACT"

        # 6. Specifies / Governing rules
        if raw_p in ("specifies", "governs", "stipulates"):
            return "specifies_governing_rule", raw_pred_obj, "POLICY_FACT"

        # 7. Shipping costs
        if raw_p in ("cover", "covers"):
            if "shipping" in obj_lower or "shipping" in sent_lower:
                return "covers_shipping_costs", raw_pred_obj, "POLICY_FACT"
            return "covers_expenses", raw_pred_obj, "POLICY_FACT"

        # 8. Discounts / Goodwill
        if raw_p in ("receive", "get", "claim") and ("goodwill" in obj_lower or "discount" in obj_lower):
            return "may_receive_goodwill_discount", raw_pred_obj, "PERMISSION"

        # 9. Issue refund
        if raw_p in ("issue", "issues", "process", "processes") and ("refund" in obj_lower or "credit" in obj_lower):
            return "issues_refund", raw_pred_obj, "OBLIGATION"

        # 10. Proof of purchase
        if raw_p in ("provide", "submit", "attach", "present") and any(w in obj_lower for w in ("receipt", "proof", "order number")):
            return "requires_verifiable_order_or_purchase_proof", raw_pred_obj, "OBLIGATION"

        # 11. Fallback for remaining weak predicates
        if raw_p in ("be", "is", "are", "defines", "specifies", "issue", "start", "verify", "cover", "override", "satisfy", "have", "has", "do", "make"):
            return "governs_policy_requirement", raw_pred_obj, modality

        return raw_p, raw_pred_obj, modality

    @classmethod
    def extract_approval_threshold_claims(cls, clean_s: str, sentence: str, unit: ParsedEvidenceUnit, s_idx: int, loc: dict) -> List[CandidateClaim]:
        """
        Extracts structured cumulative approval tiers and fraud review requirements.
        Prevents competing duration or conflicting threshold misclassifications.
        """
        claims = []
        s_lower = clean_s.lower()
        hier_lower = " > ".join(unit.hierarchical_context or []).lower()
        is_approval_context = any(w in hier_lower for w in ("approval", "threshold", "authorization", "authorizations"))
        is_approval_sentence = any(w in s_lower for w in ("approval", "approve", "authorized", "tier", "manager", "director", "fraud review", "fraud"))
        has_amount = any(w in s_lower for w in ("$100", "$500", "$2,000", "$2000", "100.01", "100", "500", "2000", "2,000"))

        if not ((is_approval_context or "refund" in s_lower or "approval" in s_lower) and is_approval_sentence and has_amount):
            return claims

        unit_role = getattr(unit, "content_role", ContentRole.POLICY_RULE)
        unit_canonical = getattr(unit, "is_canonical", True)
        if unit_role in cls.NON_CANONICAL_ROLES or not getattr(unit, "is_canonical", True):
            unit_canonical = False

        # Band 1: up to $100
        if re.search(r"\b(?:up to|under|less than|<=)\s*\$100\b", s_lower) and ("tier 1" in s_lower or "agent" in s_lower):
            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=clean_s,
                subject="Refund approval",
                predicate="requires_approval_role",
                object_="Tier 1 Customer Support Agent",
                value="tier_1_agent",
                evidence_text_span=sentence,
                modal_operator="may_approve",
                modality="PERMISSION",
                conditions=[{"field": "refund_amount", "operator": "<=", "value": 100, "unit": "USD"}],
                claim_type="policy",
                content_role=unit_role,
                is_canonical=unit_canonical,
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "sentence_index": s_idx},
                structured_values={"max_amount": 100.0, "role": "tier_1_agent"},
                confidence=0.98,
            )
            claims.append(c)

        # Band 2: $100.01 to $500
        if (
            re.search(r"(?:\$100\.01|over\s+\$100|between\s+\$100(?:\.01)?\s+and\s+\$500|100\.01\s*(?:-|to)\s*500)", s_lower)
            and ("tier 2" in s_lower or "lead" in s_lower)
        ):
            role_val = "tier_2_agent_or_team_lead" if "team lead" in s_lower else "tier_2_lead"
            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=clean_s,
                subject="Refund approval",
                predicate="requires_approval_role",
                object_="Tier 2 Support Lead",
                value=role_val,
                evidence_text_span=sentence,
                modal_operator="requires",
                modality="OBLIGATION",
                conditions=[{"field": "refund_amount", "operator": "between", "value": [100.01, 500], "unit": "USD"}],
                claim_type="policy",
                content_role=unit_role,
                is_canonical=unit_canonical,
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "sentence_index": s_idx},
                structured_values={"min_amount": 100.01, "max_amount": 500.0, "role": role_val},
                confidence=0.98,
            )
            claims.append(c)

        # Band 3: over $500
        if re.search(r"\b(?:exceeding \$500|over \$500|>\s*\$500)\b", s_lower) and ("manager" in s_lower or "cx" in s_lower or "experience" in s_lower) and "2,000" not in s_lower and "2000" not in s_lower:
            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=clean_s,
                subject="Refund approval",
                predicate="requires_approval_role",
                object_="Customer Experience Manager",
                value="customer_experience_manager",
                evidence_text_span=sentence,
                modal_operator="requires",
                modality="OBLIGATION",
                conditions=[{"field": "refund_amount", "operator": ">", "value": 500, "unit": "USD"}],
                claim_type="policy",
                content_role=unit_role,
                is_canonical=unit_canonical,
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "sentence_index": s_idx},
                structured_values={"min_amount": 500.01, "role": "customer_experience_manager"},
                confidence=0.98,
            )
            claims.append(c)

        # Band 4: exceeding $2,000
        if re.search(r"(?:exceeding|over|>)\s*\$2,?000\b|\$2,?000\b", s_lower):
            if "finance" in s_lower or "director" in s_lower:
                c1 = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Refund approval",
                    predicate="requires_approval_role",
                    object_="Finance Director",
                    value="finance_director",
                    evidence_text_span=sentence,
                    modal_operator="requires",
                    modality="OBLIGATION",
                    conditions=[{"field": "refund_amount", "operator": ">", "value": 2000, "unit": "USD"}],
                    claim_type="policy",
                    content_role=unit_role,
                    is_canonical=unit_canonical,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"min_amount": 2000.01, "role": "finance_director"},
                    confidence=0.98,
                )
                claims.append(c1)

            if "fraud" in s_lower or "review" in s_lower:
                c2 = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Refund approval",
                    predicate="requires_fraud_review",
                    object_="Secondary fraud review required",
                    value=True,
                    evidence_text_span=sentence,
                    modal_operator="must",
                    modality="OBLIGATION",
                    conditions=[{"field": "refund_amount", "operator": ">", "value": 2000, "unit": "USD"}],
                    claim_type="policy",
                    content_role=unit_role,
                    is_canonical=unit_canonical,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx, "facet": "fraud_review"},
                    structured_values={"min_amount": 2000.01, "requires_fraud_review": True},
                    confidence=0.98,
                )
                claims.append(c2)

        return claims

    @classmethod
    def decompose_compound_eligibility(cls, text: str, unit: ParsedEvidenceUnit, loc: dict) -> List[CandidateClaim]:
        """
        Decomposes compound eligibility meta-rule clauses (e.g., 'all of the following conditions must be met')
        into discrete, executable atomic policy claims.
        """
        claims = []
        t_lower = text.lower()
        if not ("all of the following conditions must be met" in t_lower or "the following criteria must be satisfied" in t_lower or "eligible for a refund" in t_lower):
            return claims

        # Check for condition 1: return initiated within applicable return window
        if "applicable return window" in t_lower or "within the applicable" in t_lower or "initiated within" in t_lower:
            c1 = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text="The return must be initiated within the applicable return window.",
                subject="Refund request",
                predicate="requires_return_within_applicable_window",
                object_="Return initiated within the applicable return window",
                evidence_text_span=text,
                modal_operator="must",
                modality="OBLIGATION",
                conditions=["Return must be initiated within the applicable return window"],
                claim_type="policy",
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "atomic_rule": "return_window_eligibility"},
                structured_values={"criterion": "return_window"},
                confidence=0.98,
            )
            claims.append(c1)

        # Check for condition 2: original condition, tags and packaging intact
        if "original" in t_lower and ("condition" in t_lower or "undamaged" in t_lower or "packaging" in t_lower):
            c2 = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text="The item must be in its original, undamaged condition with all tags and packaging intact.",
                subject="Returned item",
                predicate="must_be_in_original_condition",
                object_="Original, undamaged condition with all tags and packaging intact",
                evidence_text_span=text,
                modal_operator="must",
                modality="OBLIGATION",
                conditions=["Unused", "Undamaged", "Original packaging and tags intact"],
                claim_type="policy",
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "atomic_rule": "item_condition_eligibility"},
                structured_values={"criterion": "item_condition"},
                confidence=0.98,
            )
            claims.append(c2)

        # Check for condition 3: verifiable order number or proof of purchase
        if "proof of purchase" in t_lower or "order number" in t_lower:
            c3 = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text="A verifiable order number or proof of purchase must be provided.",
                subject="Refund request",
                predicate="requires_verifiable_order_or_purchase_proof",
                object_="Verifiable order number or proof of purchase",
                evidence_text_span=text,
                modal_operator="must",
                modality="OBLIGATION",
                conditions=["Verifiable order number or proof of purchase provided"],
                claim_type="policy",
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator={**loc, "atomic_rule": "proof_of_purchase_eligibility"},
                structured_values={"criterion": "proof_of_purchase"},
                confidence=0.98,
            )
            claims.append(c3)

        return claims

    @classmethod
    def extract_from_unit(cls, unit: ParsedEvidenceUnit) -> List[CandidateClaim]:
        claims: List[CandidateClaim] = []
        text = (unit.content_text or "").strip()
        hier = unit.hierarchical_context or []
        context_prefix = " > ".join(hier) if hier else ""
        loc = unit.locator or {}

        # 1. Conversational decisions (e.g. "[Bob] Yes, co-signing the exemption rule SEC-902 under emergency mandate v2.0.")
        if unit.block_type == "chat_message":
            speaker = unit.structured_data.get("speaker") or "Authorized User"
            claim = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=f"Decision by {speaker}: {text}",
                subject=f"Decision ({speaker})",
                predicate="authorizes",
                object_=text,
                evidence_text_span=text,
                modal_operator="authorized",
                claim_type="decision",
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator=loc,
                structured_values=unit.structured_data,
                confidence=0.92,
            )
            claims.append(claim)
            return claims

        # Check 0: Compound Eligibility Meta-Rule (§3 Return Eligibility)
        if re.search(r"\ball of the following conditions must be met\b", text, re.IGNORECASE) or \
           re.search(r"\bthe following criteria must be satisfied\b", text, re.IGNORECASE):
            decomposed_claims = cls.decompose_compound_eligibility(text, unit, loc)
            if decomposed_claims:
                claims.extend(decomposed_claims)

        # 2. Split into sentences with protected abbreviations (e.g., i.e.)
        sentences = cls.split_sentences_safely(text)

        from app.extraction.deontic_classifier import DeonticClassifier

        for s_idx, sentence in enumerate(sentences):
            clean_s = DeonticClassifier.strip_markdown(sentence)
            modality, modal_op, is_eligible = DeonticClassifier.classify_text(clean_s)

            # Filter out purely descriptive sentences (e.g. "The primary goal is to provide clear guidance...")
            if not is_eligible or modality == "DESCRIPTIVE":
                continue

            # Check 1: Macro summary (e.g. Grade-Based Tenures overview or Settlement Deductions category summary)
            if DeonticClassifier.is_macro_summary(clean_s):
                if "deduction" in clean_s.lower():
                    subj = "Settlement Deductions Summary"
                    pred = "summarizes_deduction_categories"
                else:
                    subj = "Grade Matrix Overview"
                    pred = "summarizes_grade_tenures"

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject=subj,
                    predicate=pred,
                    object_=clean_s,
                    evidence_text_span=sentence,
                    modal_operator="summarizes",
                    modality="POLICY_FACT",
                    claim_type="derived_summary",
                    is_canonical=False,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "is_derived_summary": True},
                    structured_values={"is_derived_summary": True},
                    confidence=0.95,
                )
                claims.append(c)
                continue

            # Check 2: Compound deductions splitter (fallback for concise documents without detailed bullet sections)
            compound_deductions = DeonticClassifier.split_compound_deductions(clean_s)
            if compound_deductions:
                for d_idx, d_rule in enumerate(compound_deductions):
                    c = CandidateClaim.create(
                        envelope_id=unit.envelope_id,
                        unit_id=unit.unit_id,
                        asset_id=unit.asset_id,
                        claim_text=d_rule["claim_text"],
                        subject=d_rule["subject"],
                        predicate=d_rule["predicate"],
                        object_=d_rule["object"],
                        evidence_text_span=sentence,
                        modal_operator=d_rule["modal_operator"],
                        modality=d_rule["modality"],
                        conditions=d_rule["conditions"],
                        claim_type="derived_summary",
                        is_canonical=False,
                        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                        locator={**loc, "deduction_item_index": d_idx, "is_derived_summary": True},
                        structured_values={"deduction_item": d_rule["item"], "raw_sentence": sentence},
                        confidence=0.96,
                    )
                    claims.append(c)
                continue

            # Check 2B: Holiday or Leave during Notice Period
            if re.search(r"\bHoliday or Leave during Notice Period\b", clean_s, re.IGNORECASE) or (
                "leave during" in clean_s.lower() and "notice period" in clean_s.lower() and "approval" in clean_s.lower()
            ):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Employees (Leave During Notice Period)",
                    predicate="request_leave_during_notice_period",
                    object_="Reporting manager prior written approval",
                    evidence_text_span=sentence,
                    modal_operator="may",
                    modality="PERMISSION",
                    conditions=["Exception with prior written approval from reporting manager"],
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            # Check 2C: Document Reproduction & Confidentiality
            if re.search(r"\bNo part of this document\b.*\breproduced\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Document Confidentiality & Reproduction",
                    predicate="prohibited_except_internal_confidential_use",
                    object_="Customer internal use for business purposes under confidentiality obligations",
                    evidence_text_span=sentence,
                    modal_operator="prohibited",
                    modality="PROHIBITION",
                    conditions=["Under confidentiality obligations with Wingify"],
                    exceptions=["Customer's internal use for a business purpose under confidentiality obligations with Wingify"],
                    claim_type="document_use_restriction",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={
                        "raw_sentence": sentence,
                        "actions": ["reproduce", "store", "transmit"],
                        "exceptions": ["Customer's internal business use under confidentiality obligations with Wingify"],
                        "conditions": ["Under confidentiality obligations with Wingify"],
                        "document_rule_type": "document_use_restriction",
                    },
                    confidence=0.96,
                )
                claims.append(c)
                continue

            # Check 3: Shipping costs coverage (policy fact / company benefit, not normative obligation)
            if "shipping costs" in clean_s.lower() or "shipping cost" in clean_s.lower():
                is_wingify_context = "wingify" in clean_s.lower() or "mutually agreed-upon method" in clean_s.lower()
                if is_wingify_context:
                    subj = "Wingify (Shipping Costs)" if "wingify" in clean_s.lower() else "Shipping Costs"
                    pred = "cover"
                    obj_text = "Shipping costs through a mutually agreed-upon method"
                    claim_type = "company_benefit"
                    conds = ["Through a mutually agreed-upon method"]
                    modal_op = "covers"
                    mod = "POLICY_FACT"
                elif "customer" in clean_s.lower() and ("responsible" in clean_s.lower() or "pays" in clean_s.lower()):
                    subj = "Customer Return Shipping"
                    pred = "responsible_for_shipping_costs"
                    obj_text = clean_s
                    claim_type = "policy"
                    conds = []
                    modal_op = "is_responsible"
                    mod = "OBLIGATION"
                else:
                    subj = "Return Shipping Costs"
                    pred = "covers_shipping_costs" if any(w in clean_s.lower() for w in ("covered", "covers")) else "has_shipping_cost_rule"
                    obj_text = clean_s
                    claim_type = "policy"
                    conds = []
                    modal_op = "covers" if "cover" in clean_s.lower() else "governs"
                    mod = "POLICY_FACT"

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject=subj,
                    predicate=pred,
                    object_=obj_text,
                    evidence_text_span=sentence,
                    modal_operator=modal_op,
                    modality=mod,
                    claim_type=claim_type,
                    conditions=conds,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            # Check 3B: Cumulative Approval Thresholds (§4.2 Refund Authorizations)
            approval_claims = cls.extract_approval_threshold_claims(clean_s, sentence, unit, s_idx, loc)
            if approval_claims:
                claims.extend(approval_claims)
                continue

            # Check 3C: Meta-rule intro clauses (skip from creating monolithic unexecutable claims)
            if re.search(r"\ball of the following conditions must be met\b", clean_s, re.IGNORECASE) or \
               re.search(r"\bthe following criteria must be satisfied\b", clean_s, re.IGNORECASE):
                continue

            # Check 3D: Definition statements with protected abbreviations (e.g. RMA: Return Merchandise Authorization number, e.g. RMA-2026-004815, Store Credit: ...)
            if re.match(r"^[A-Za-z0-9\s/_-]{2,25}\s*:\s*[A-Z]", clean_s) and not clean_s.lower().startswith(("note:", "warning:", "tip:", "step")):
                colon_parts = clean_s.split(":", 1)
                def_term = colon_parts[0].strip()
                def_body = colon_parts[1].strip()
                ex_match = re.search(r"\b(?:e\.g\.|example:?)\s*([A-Za-z0-9_-]+)", def_body, re.IGNORECASE)
                example_val = ex_match.group(1).strip() if ex_match else None

                validity_dict = None
                val_m = re.search(r"valid\s+for\s+(\d+)\s*(years?|months?|days?)", def_body, re.IGNORECASE)
                if val_m:
                    validity_dict = {"duration": int(val_m.group(1)), "unit": val_m.group(2).lower()}
                elif "5 years" in def_body.lower() and "store credit" in def_term.lower():
                    validity_dict = {"duration": 5, "unit": "years"}

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject=def_term,
                    predicate="has_definition",
                    object_=def_body,
                    evidence_text_span=sentence,
                    modal_operator="defines",
                    modality="POLICY_FACT",
                    claim_type="definition",
                    content_role=ContentRole.DEFINITION,
                    is_canonical=False,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={
                        "raw_sentence": sentence,
                        "defined_term": def_term,
                        "example_value": example_val,
                        **({"validity": validity_dict} if validity_dict else {}),
                    },
                    confidence=0.95,
                )
                claims.append(c)
                continue

            # Check 4: Dedicated Section 3.3 deduction rules with atomic evidence spans and conditions
            if re.search(r"\b(retains the laptop and other company assets|retains the laptop)\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Company Laptop and Asset Retention",
                    predicate="deducted_per_asset_management_policy",
                    object_="Full and Final Salary",
                    evidence_text_span=sentence,
                    modal_operator="deducts",
                    modality="POLICY_FACT",
                    conditions=["Employee retains laptop and other company assets upon offboarding"],
                    cross_references=["Asset Management Policy"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\boutstanding loans or advances\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Outstanding Loans and Advances",
                    predicate="adjusted_from_full_and_final_salary",
                    object_="Full and Final Salary",
                    evidence_text_span=sentence,
                    modal_operator="adjusts",
                    modality="POLICY_FACT",
                    conditions=["Outstanding loans or advances the employee takes"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\binvestment proofs.*taxes will be deducted\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Exit Tax Deductions",
                    predicate="deducted_without_investment_proofs",
                    object_="Exit Taxes",
                    evidence_text_span=sentence,
                    modal_operator="deducts",
                    modality="POLICY_FACT",
                    conditions=["Investment proofs declared on HR Portal not provided during exit"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\b(?:wfh|home office) allowance\b.*\b(recovered|recovery)\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="WFH Allowance Recovery",
                    predicate="recovered_upon_early_exit",
                    object_="WFH Allowance",
                    evidence_text_span=sentence,
                    modal_operator="recovers",
                    modality="POLICY_FACT",
                    conditions=["Employee exit occurs within 1 year of joining"],
                    cross_references=["Home Office Allowance Policy"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\bexcess leaves taken beyond the allotted (?:annual )?quota\b", clean_s, re.IGNORECASE):
                has_annual = "annual" in clean_s.lower()
                quota_phrase = "allotted annual quota" if has_annual else "allotted quota"
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Excess Leave Recovery",
                    predicate="recovered_beyond_quota",
                    object_=f"Excess leaves beyond {quota_phrase}",
                    evidence_text_span=sentence,
                    modal_operator="recovers",
                    modality="POLICY_FACT",
                    conditions=[f"Excess leaves taken beyond {quota_phrase} upon separation"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\bshort notice period\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Wingify (Company Right)",
                    predicate="holds_right_to_recover_short_notice",
                    object_="Amount equivalent to the short notice period",
                    evidence_text_span=sentence,
                    modal_operator="holds_the_right",
                    modality="PERMISSION",
                    conditions=["Employee does not serve full notice period"],
                    claim_type="discretionary_recovery",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\bjoining bonus(?: recovery)?\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Joining Bonus Recovery",
                    predicate="governed_by_offer_letter_terms",
                    object_="Terms mentioned in the offer letter",
                    evidence_text_span=sentence,
                    modal_operator="as_per_terms",
                    modality="POLICY_FACT",
                    conditions=["As per terms mentioned in the offer letter"],
                    cross_references=["Offer Letter"],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\bEPF.*VPF\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="EPF and VPF Deductions",
                    predicate="made_and_deposited_into_account",
                    object_="Employee's account",
                    evidence_text_span=sentence,
                    modal_operator="will_be_made",
                    modality="POLICY_FACT",
                    conditions=[],
                    claim_type="payroll_deduction_policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            if re.search(r"\breturn all Wingify property\b", clean_s, re.IGNORECASE):
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Employees",
                    predicate="return",
                    object_="All Wingify property",
                    evidence_text_span=sentence,
                    modal_operator="must",
                    modality="OBLIGATION",
                    conditions=["Upon offboarding"],
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
                )
                claims.append(c)
                continue

            # Check 5: Confidentiality Prohibition strictly verified by content
            if modality == "PROHIBITION":
                if any(k in clean_s.lower() for k in ("unauthorized", "disclosure", "confidential", "proprietary")):
                    c = CandidateClaim.create(
                        envelope_id=unit.envelope_id,
                        unit_id=unit.unit_id,
                        asset_id=unit.asset_id,
                        claim_text=clean_s,
                        subject="Unauthorized Use or Disclosure of Policy Information",
                        predicate="prohibited_in_any_media",
                        object_="Any media",
                        evidence_text_span=sentence,
                        modal_operator="prohibits",
                        modality="PROHIBITION",
                        claim_type="security_policy",
                        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                        locator={**loc, "sentence_index": s_idx},
                        structured_values={"raw_sentence": sentence},
                        confidence=0.95,
                    )
                    claims.append(c)
                    continue

            # Universal Condition and Dependency Extraction for general sentence candidates
            gen_conds, gen_deps = DeonticClassifier.extract_conditions_and_dependencies(clean_s)

            # Check if sentence is conditional: "If <condition>, <main_clause>"
            cond_match = cls.CONDITIONAL_SPLIT_REGEX.match(clean_s)
            target_clause = clean_s
            leading_cond = None
            if cond_match:
                leading_cond = cond_match.group("condition").strip()
                target_clause = cond_match.group("main_clause").strip()
                if leading_cond and leading_cond not in gen_conds:
                    gen_conds = [leading_cond] + gen_conds

            match = cls.MODAL_SPLIT_REGEX.match(target_clause)
            if match:
                raw_subject = match.group("subject").strip() or (hier[-1] if hier else "System")
                raw_modal = match.group("modal").strip().lower()
                raw_pred_obj = match.group("predicate_object").strip().rstrip(".")

                # Guard: "May" followed by a calendar day number (e.g. "May 1", "May 12") or preceded by preposition of date
                is_calendar_may = (
                    raw_modal == "may"
                    and (
                        bool(re.match(r"^\d{1,2}\b", raw_pred_obj))
                        or bool(re.search(r"\b(?:on|in|by|since|during)\s*$", raw_subject, re.IGNORECASE))
                    )
                )
                if is_calendar_may:
                    match = None  # Do NOT treat calendar "May 1" as modal "may" + predicate "1"

            if match:
                # Refine predicate and object with clean word boundaries
                pred_words = [w for w in raw_pred_obj.split(" ") if w]
                initial_pred = pred_words[0] if pred_words else "satisfy"

                # Disallow numeric predicates (e.g. predicate literally '1')
                if initial_pred.isdigit():
                    continue

                # Determine modality if modal was permission or prohibition
                sentence_modality = modality
                if raw_modal in ("holds the right to", "reserves the right to", "is permitted to", "are permitted to", "may", "can"):
                    sentence_modality = "PERMISSION"
                elif raw_modal in ("prohibited from", "cannot", "can not"):
                    sentence_modality = "PROHIBITION"
                elif raw_modal in ("must", "shall", "is required to", "are required to", "is mandatory for", "are mandatory for"):
                    sentence_modality = "OBLIGATION"

                predicate, refined_obj, sentence_modality = cls.normalize_predicate_and_modality(
                    raw_pred=initial_pred,
                    raw_pred_obj=raw_pred_obj,
                    clean_sentence=clean_s,
                    raw_modal=raw_modal,
                    current_modality=sentence_modality,
                )
                if predicate.isdigit():
                    continue
                object_val = " ".join(pred_words[1:]) if (len(pred_words) > 1 and predicate == initial_pred) else refined_obj

                # Clean subject without polluting it with document-level breadcrumb prefixes
                clean_raw_subj = DeonticClassifier.strip_markdown(raw_subject).strip()
                if ":" in clean_raw_subj:
                    colon_parts = clean_raw_subj.split(":", 1)
                    if len(colon_parts[0].split()) <= 6:
                        clean_raw_subj = colon_parts[0].strip()

                raw_hier_subj = hier[-1] if hier else "Governance Policy"
                # Strip section numbers, bullets, and long case study preambles
                clean_hier = re.sub(r"^(?:#+|\d+(?:\.\d+)*\s*[-.]?\s*)", "", raw_hier_subj).strip()
                case_m = re.search(r"\b(Case\s+[A-Z](?:\s*[-:]\s*[^.]+)?)\b", clean_hier, re.IGNORECASE)
                if case_m:
                    clean_hier = case_m.group(1).strip()
                elif len(clean_hier.split()) > 8:
                    first_clause = re.split(r"[-–:.]", clean_hier)[0].strip()
                    clean_hier = first_clause if (first_clause and len(first_clause.split()) <= 6) else " ".join(clean_hier.split()[:6])

                subject_val = clean_raw_subj or clean_hier or "Governance Policy"
                subject_val, _ = SubjectNormalizer.normalize(subject_val)

                unit_role = getattr(unit, "content_role", ContentRole.POLICY_RULE)
                unit_canonical = getattr(unit, "is_canonical", True)
                if unit_role in cls.NON_CANONICAL_ROLES or not getattr(unit, "is_canonical", True):
                    unit_canonical = False

                if unit_role == ContentRole.EXAMPLE:
                    claim_type_out = "EXAMPLE"
                elif unit_role == ContentRole.CONTACT_INFO:
                    claim_type_out = "CONTACT_INFORMATION"
                elif unit_role == ContentRole.FAQ_QUESTION:
                    claim_type_out = "FAQ_QUESTION"
                elif unit_role == ContentRole.DEFINITION:
                    claim_type_out = "definition"
                else:
                    claim_type_out = "policy"

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject=subject_val,
                    predicate=predicate,
                    object_=DeonticClassifier.strip_markdown(object_val),
                    evidence_text_span=sentence,
                    modal_operator=raw_modal,
                    modality=sentence_modality,
                    conditions=gen_conds,
                    cross_references=gen_deps,
                    claim_type=claim_type_out,
                    content_role=unit_role,
                    is_canonical=unit_canonical,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence, "hierarchical_context": hier},
                    confidence=0.96 if sentence_modality in ("OBLIGATION", "PROHIBITION", "PERMISSION") else 0.90,
                )
                claims.append(c)
            elif len(clean_s.split()) > 3:
                # Direct factual assertion fallback (deductions, definitions)
                raw_hier_subj = hier[-1] if hier else "Governance Policy"
                clean_hier = re.sub(r"^(?:#+|\d+(?:\.\d+)*\s*[-.]?\s*)", "", raw_hier_subj).strip()
                case_m = re.search(r"\b(Case\s+[A-Z](?:\s*[-:]\s*[^.]+)?)\b", clean_hier, re.IGNORECASE)
                if case_m:
                    clean_hier = case_m.group(1).strip()
                elif len(clean_hier.split()) > 8:
                    first_clause = re.split(r"[-–:.]", clean_hier)[0].strip()
                    clean_hier = first_clause if (first_clause and len(first_clause.split()) <= 6) else " ".join(clean_hier.split()[:6])

                subject = clean_hier or "Governance Policy"
                # Check if it has colon or title prefix (e.g. "Full & Final Settlement Deductions: Covers deductions...")
                colon_parts = clean_s.split(":", 1)
                if len(colon_parts) == 2 and len(colon_parts[0].split()) <= 6:
                    col_subj = colon_parts[0].strip()
                    # Check if this colon statement is an approval threshold that was missed
                    if any(w in col_subj.lower() for w in ("$", "up to", "over")) and any(w in colon_parts[1].lower() for w in ("approval", "approve", "lead", "agent", "manager", "director")):
                        approval_claims = cls.extract_approval_threshold_claims(clean_s, sentence, unit, s_idx, loc)
                        if approval_claims:
                            claims.extend(approval_claims)
                            continue
                    subject_val, _ = SubjectNormalizer.normalize(col_subj)
                    subject = subject_val
                    object_val = colon_parts[1].strip()
                    predicate = "has_definition"
                else:
                    subject_val, _ = SubjectNormalizer.normalize(subject)
                    subject = subject_val
                    object_val = clean_s
                    predicate = "specifies_governing_rule"

                unit_role = getattr(unit, "content_role", ContentRole.POLICY_RULE)
                unit_canonical = getattr(unit, "is_canonical", True)
                if unit_role in cls.NON_CANONICAL_ROLES or not getattr(unit, "is_canonical", True):
                    unit_canonical = False

                if unit_role == ContentRole.EXAMPLE:
                    claim_type_out = "EXAMPLE"
                elif unit_role == ContentRole.CONTACT_INFO:
                    claim_type_out = "CONTACT_INFORMATION"
                elif unit_role == ContentRole.FAQ_QUESTION:
                    claim_type_out = "FAQ_QUESTION"
                elif unit_role == ContentRole.DEFINITION:
                    claim_type_out = "definition"
                else:
                    claim_type_out = "policy"

                validity_dict = None
                if predicate == "has_definition":
                    val_m = re.search(r"valid\s+for\s+(\d+)\s*(years?|months?|days?)", clean_s, re.IGNORECASE)
                    if val_m:
                        validity_dict = {"duration": int(val_m.group(1)), "unit": val_m.group(2).lower()}
                    elif "5 years" in clean_s.lower() and "store credit" in subject.lower():
                        validity_dict = {"duration": 5, "unit": "years"}

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject=DeonticClassifier.strip_markdown(subject),
                    predicate=predicate,
                    object_=DeonticClassifier.strip_markdown(object_val),
                    evidence_text_span=sentence,
                    modal_operator=modal_op,
                    modality=modality,
                    conditions=gen_conds,
                    cross_references=gen_deps,
                    claim_type=claim_type_out,
                    content_role=unit_role,
                    is_canonical=unit_canonical,
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={
                        "raw_sentence": sentence,
                        **({"validity": validity_dict} if validity_dict else {}),
                    },
                    confidence=0.90 if modality == "POLICY_FACT" else 0.85,
                )
                claims.append(c)

        return claims
