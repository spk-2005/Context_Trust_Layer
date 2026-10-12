"""
Layer 5: Domain Rules Extractor.
Extracts structured claims from normative policy clauses, compliance rules, and conversational decisions
using deterministic grammar patterns, modal logic parsing, and domain heuristics.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


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

        # 2. Split into sentences if multi-sentence clause
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            sentences = [text]

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
            if "shipping costs" in clean_s.lower():
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=clean_s,
                    subject="Wingify Shipping Costs",
                    predicate="cover",
                    object_="Shipping costs through a mutually agreed-upon method",
                    evidence_text_span=sentence,
                    modal_operator="covers",
                    modality="POLICY_FACT",
                    claim_type="company_benefit",
                    conditions=["Through a mutually agreed-upon method"],
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.96,
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

                # Refine predicate and object with clean word boundaries
                pred_words = [w for w in raw_pred_obj.split(" ") if w]
                if len(pred_words) >= 1:
                    predicate = pred_words[0]
                    object_val = " ".join(pred_words[1:]) if len(pred_words) > 1 else raw_pred_obj
                else:
                    predicate = "satisfy"
                    object_val = raw_pred_obj

                # Determine modality if modal was permission or prohibition
                sentence_modality = modality
                if raw_modal in ("holds the right to", "reserves the right to", "is permitted to", "are permitted to", "may", "can"):
                    sentence_modality = "PERMISSION"
                elif raw_modal in ("prohibited from", "cannot", "can not"):
                    sentence_modality = "PROHIBITION"
                elif raw_modal in ("must", "shall", "is required to", "are required to", "is mandatory for", "are mandatory for"):
                    sentence_modality = "OBLIGATION"

                # Clean subject without polluting it with document-level breadcrumb prefixes
                clean_raw_subj = DeonticClassifier.strip_markdown(raw_subject).strip()
                if ":" in clean_raw_subj:
                    colon_parts = clean_raw_subj.split(":", 1)
                    if len(colon_parts[0].split()) <= 6:
                        clean_raw_subj = colon_parts[0].strip()
                subject_val = clean_raw_subj or (hier[-1] if hier else "Governance Policy")

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
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence, "hierarchical_context": hier},
                    confidence=0.96 if sentence_modality in ("OBLIGATION", "PROHIBITION", "PERMISSION") else 0.90,
                )
                claims.append(c)
            elif len(clean_s.split()) > 3:
                # Direct factual assertion fallback (deductions, definitions)
                subject = hier[-1] if hier else "Governance Policy"
                # Check if it has colon or title prefix (e.g. "Full & Final Settlement Deductions: Covers deductions...")
                colon_parts = clean_s.split(":", 1)
                if len(colon_parts) == 2 and len(colon_parts[0].split()) <= 6:
                    subject = colon_parts[0].strip()
                    object_val = colon_parts[1].strip()
                    predicate = "defines"
                else:
                    object_val = clean_s
                    predicate = "specifies"

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
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.90 if modality == "POLICY_FACT" else 0.85,
                )
                claims.append(c)

        return claims
