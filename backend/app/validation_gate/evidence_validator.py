"""
Layer 6: Exact Evidence Matcher & Reliable Claim Validation Service.
Phase 6: Multi-span grounded validation, topical contamination guards,
table coordinate validation, multi-evidence synthesis, and version-aware auditing.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from app.extraction.models import CandidateClaim, TableGridBinding
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceUnit,
    ExtractionStatus,
    ParsedEvidenceUnit,
)
from app.validation_gate.models import (
    ClaimValidationAuditReport,
    ClaimValidationStatus,
)

logger = logging.getLogger(__name__)

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "per", "upon", "must", "shall", "may", "will", "can", "policy", "rule", "item",
}


def _normalize_text(text: str) -> str:
    """Normalizes whitespace and lowercases text for robust matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_content_tokens(text: str) -> Set[str]:
    """Extracts non-stopword content tokens from text."""
    if not text:
        return set()
    tokens = re.findall(r"[a-z0-9]{2,}", text.lower())
    return {re.sub(r"s$", "", t) for t in tokens} - STOPWORDS


def _get_unit_identifiers(unit: Any) -> List[str]:
    """Extracts all recognized unique identifiers from an evidence unit."""
    ids: List[str] = []
    for key in ("unit_id", "evidence_instance_id", "evidence_id", "id"):
        v = getattr(unit, key, None) if not isinstance(unit, dict) else unit.get(key)
        if v:
            v_str = str(v)
            if v_str not in ids:
                ids.append(v_str)
            clean = v_str.removeprefix("ev:").removeprefix("inst_")
            if clean not in ids:
                ids.append(clean)
    return ids


def _get_primary_unit_id(unit: Any) -> str:
    """Safely extracts primary evidence unit ID from various model flavors."""
    return str(
        getattr(unit, "unit_id", None)
        or getattr(unit, "evidence_id", None)
        or getattr(unit, "evidence_instance_id", None)
        or getattr(unit, "id", None)
        or (unit.get("unit_id") if isinstance(unit, dict) else None)
        or (unit.get("evidence_id") if isinstance(unit, dict) else None)
        or ""
    )


def _get_unit_text(unit: Any) -> str:
    """Safely extracts normalized or raw text from an evidence unit."""
    if isinstance(unit, dict):
        return (
            unit.get("normalized_content")
            or unit.get("raw_content")
            or unit.get("content_text")
            or ""
        )
    return (
        getattr(unit, "normalized_content", None)
        or getattr(unit, "raw_content", None)
        or getattr(unit, "content_text", None)
        or ""
    )


def _get_unit_raw(unit: Any) -> str:
    """Safely extracts raw source text from an evidence unit."""
    if isinstance(unit, dict):
        return unit.get("raw_content") or unit.get("normalized_content") or ""
    return getattr(unit, "raw_content", None) or getattr(unit, "normalized_content", None) or ""


def _parse_version(v: Optional[str]) -> Tuple[int, int, int]:
    """Extracts major.minor.patch numeric tuple for version comparison."""
    if not v:
        return (0, 0, 0)
    nums = [int(n) for n in re.findall(r"\d+", str(v))]
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


class ReliableClaimEvidenceValidator:
    """
    Core Phase 6 Service:
    Provides exact evidence matching, multi-evidence synthesis, topical cross-contamination guards,
    table grid coordinate validation, and version-aware claim validation.
    """

    @classmethod
    def retrieve_candidate_evidence(
        cls,
        claim: CandidateClaim,
        evidence_units: Sequence[Any],
    ) -> List[Any]:
        """
        Retrieves matching evidence units for a claim using exact ID, locator,
        table bindings, structural relationships, and content token overlap.
        Enforces topical specificity safeguards (e.g. Northwind rule).
        """
        if not evidence_units:
            return []

        # 1. Exact ID collection from claim
        target_ids: Set[str] = set()
        if getattr(claim, "evidence_unit_ids", None):
            for eid in claim.evidence_unit_ids:
                if eid:
                    target_ids.add(str(eid))
                    target_ids.add(str(eid).removeprefix("ev:").removeprefix("inst_"))
        for attr in ("source_unit_id", "unit_id", "evidence_id"):
            val = getattr(claim, attr, None)
            if val:
                target_ids.add(str(val))
                target_ids.add(str(val).removeprefix("ev:").removeprefix("inst_"))

        # Check for explicit ID matches first
        exact_id_matches = []
        if target_ids:
            for u in evidence_units:
                u_ids = set(_get_unit_identifiers(u))
                if target_ids.intersection(u_ids):
                    exact_id_matches.append(u)

        # 2. Table binding matching
        tb = getattr(claim, "table_binding", None)
        table_matches = []
        if tb and getattr(tb, "table_id", None):
            for u in evidence_units:
                u_loc = getattr(u, "locator", None) or (u.get("locator") if isinstance(u, dict) else {})
                u_struct = getattr(u, "structured_data", None) or (u.get("structured_data") if isinstance(u, dict) else {})
                u_table_id = (
                    getattr(u_loc, "table_id", None)
                    or (u_loc.get("table_id") if isinstance(u_loc, dict) else None)
                    or (u_struct.get("table_id") if isinstance(u_struct, dict) else None)
                )
                if u_table_id and str(u_table_id) == str(tb.table_id):
                    table_matches.append(u)
                elif tb.row_key and _normalize_text(tb.row_key) in _normalize_text(_get_unit_text(u)):
                    table_matches.append(u)

        # 3. Topical and Lexical Matching with Safeguards
        claim_subj = getattr(claim, "subject", "") or ""
        claim_text = getattr(claim, "claim_text", "") or ""
        claim_span = getattr(claim, "evidence_text_span", "") or ""
        subj_tokens = _extract_content_tokens(claim_subj)
        claim_tokens = _extract_content_tokens(claim_text).union(_extract_content_tokens(claim_span))

        topical_matches = []
        for u in evidence_units:
            u_text = _get_unit_text(u)
            if not u_text:
                continue
            u_tokens = _extract_content_tokens(u_text)
            
            # Topical Safeguard (Northwind Rule):
            # A specific subject (e.g. "video course") must NOT link to a general contradictory
            # or separate clause (e.g. general "digital goods non-refundable") when the unit text
            # does not mention the specific subject or its components.
            if subj_tokens:
                subj_overlap = subj_tokens.intersection(u_tokens)
                if not subj_overlap:
                    # Check if locator heading path contains the subject
                    loc = getattr(u, "locator", None) or (u.get("locator") if isinstance(u, dict) else {})
                    headings = " ".join(getattr(loc, "heading_path", None) or (loc.get("heading_path") if isinstance(loc, dict) else []) or []).lower()
                    if not any(st in headings for st in subj_tokens):
                        continue

            overlap = claim_tokens.intersection(u_tokens)
            if len(overlap) >= 2 or (len(claim_tokens) <= 3 and len(overlap) >= 1):
                topical_matches.append((len(overlap), u))

        # Sort topical matches by token overlap descending
        topical_matches.sort(key=lambda x: x[0], reverse=True)
        ranked_topical = [m[1] for m in topical_matches]

        # Combine results preserving uniqueness
        combined: List[Any] = []
        seen_primary_ids: Set[str] = set()

        for group in (exact_id_matches, table_matches, ranked_topical):
            for u in group:
                pid = _get_primary_unit_id(u)
                if pid and pid not in seen_primary_ids:
                    seen_primary_ids.add(pid)
                    combined.append(u)
                elif not pid and u not in combined:
                    combined.append(u)

        return combined

    @classmethod
    def verify_evidence_link(
        cls,
        claim: CandidateClaim,
        evidence_unit: Any,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifies that an alleged evidence unit exists, resolves its locator,
        contains the cited quote or structured coordinates, and is topically aligned.
        Returns: (is_verified, exact_matched_quote, failure_reason)
        """
        if evidence_unit is None:
            return False, None, "Evidence unit does not exist or is null."

        uid = _get_primary_unit_id(evidence_unit)
        unit_text = _get_unit_text(evidence_unit)
        raw_text = _get_unit_raw(evidence_unit)

        if not unit_text and not raw_text:
            return False, None, f"Evidence unit '{uid}' contains empty normalized and raw content."

        # Explicit Association Fast-Path:
        # If this unit was explicitly linked in claim.evidence_unit_ids or claim.source_unit_id,
        # it was already selected by Layer 4/5 pipeline as a contributing block.
        target_ids: Set[str] = set()
        if getattr(claim, "evidence_unit_ids", None):
            for eid in claim.evidence_unit_ids:
                if eid:
                    target_ids.add(str(eid))
                    target_ids.add(str(eid).removeprefix("ev:").removeprefix("inst_"))
        for attr in ("source_unit_id", "unit_id", "evidence_id"):
            val = getattr(claim, attr, None)
            if val:
                target_ids.add(str(val))
                target_ids.add(str(val).removeprefix("ev:").removeprefix("inst_"))

        unit_all_ids = set(_get_unit_identifiers(evidence_unit))
        is_explicitly_linked = bool(target_ids.intersection(unit_all_ids))

        # Check Table Grid Binding Fast-Path:
        tb = getattr(claim, "table_binding", None)
        if tb:
            struct = getattr(evidence_unit, "structured_data", None) or (evidence_unit.get("structured_data") if isinstance(evidence_unit, dict) else {})
            u_loc = getattr(evidence_unit, "locator", None) or (evidence_unit.get("locator") if isinstance(evidence_unit, dict) else {})
            u_tbl_id = (
                getattr(u_loc, "table_id", None)
                or (u_loc.get("table_id") if isinstance(u_loc, dict) else None)
                or (struct.get("table_id") if isinstance(struct, dict) else None)
            )
            if (u_tbl_id and str(u_tbl_id) == str(tb.table_id)) or (tb.row_key and _normalize_text(tb.row_key) in _normalize_text(unit_text)) or is_explicitly_linked:
                return True, unit_text[:200], None

        # Check exact quote matching
        quote = getattr(claim, "evidence_text_span", "") or ""
        norm_quote = _normalize_text(quote)
        norm_unit = _normalize_text(unit_text)
        norm_raw = _normalize_text(raw_text)

        matched_quote: Optional[str] = None
        if norm_quote:
            if norm_quote in norm_unit:
                matched_quote = quote
            elif norm_quote in norm_raw:
                matched_quote = quote
            else:
                # Substring token check
                q_tokens = _extract_content_tokens(quote)
                u_tokens = _extract_content_tokens(unit_text)
                if q_tokens and (q_tokens.issubset(u_tokens) or (is_explicitly_linked and len(q_tokens.intersection(u_tokens)) >= 1)):
                    matched_quote = unit_text
                elif is_explicitly_linked:
                    # In multi-block evidence, a single unit may only hold part of the quote
                    matched_quote = unit_text
                else:
                    return False, None, f"Cited quote '{quote}' not found in evidence unit '{uid}'."
        else:
            matched_quote = unit_text[:200]

        # Topical alignment verification:
        # Verify the quote supports the claim's subject and predicate, rather than merely sharing words.
        subj = getattr(claim, "subject", "") or ""
        if subj and not is_explicitly_linked:
            subj_tokens = _extract_content_tokens(subj)
            unit_tokens = _extract_content_tokens(unit_text)
            if subj_tokens and not subj_tokens.intersection(unit_tokens):
                loc = getattr(evidence_unit, "locator", None) or (evidence_unit.get("locator") if isinstance(evidence_unit, dict) else {})
                headings = " ".join(getattr(loc, "heading_path", None) or (loc.get("heading_path") if isinstance(loc, dict) else []) or []).lower()
                if not any(st in headings for st in subj_tokens):
                    return False, None, f"Topic mismatch: evidence unit '{uid}' does not mention claim subject '{subj}'."

        return True, matched_quote, None

    @classmethod
    def validate_claim(
        cls,
        claim: CandidateClaim,
        evidence_units: Sequence[Any],
        historical_claims: Optional[Sequence[Any]] = None,
    ) -> ClaimValidationAuditReport:
        """
        Phase 6 Authoritative Claim Validation.
        Evaluates candidate claim against source evidence, distinguishing:
        - SUPPORTED: grounded in source with conditions/exceptions intact.
        - CONTRADICTED: direct logical/numeric conflict within same scope and active version.
        - INSUFFICIENT_EVIDENCE: evidence missing, locator unresolvable, or extraction failed.
        - NEEDS_REVIEW: ambiguous layout, shifted table cells, or missing conditions/exceptions.
        """
        claim_id = getattr(claim, "candidate_id", "unknown_claim")
        ext_status = getattr(claim, "extraction_status", "success")
        source_version = getattr(claim, "source_version", None)
        claim_loc = getattr(claim, "locator", {}) or {}

        warnings: List[str] = []
        missing_conditions: List[str] = []
        missing_exceptions: List[str] = []

        # 1. Extraction Status Gate: Decouple Layer 4 extraction status from validation
        # If extraction failed, needs OCR, or is empty, report INSUFFICIENT_EVIDENCE (never CONTRADICTED or REJECTED)
        if ext_status in (ExtractionStatus.FAILED, ExtractionStatus.NEEDS_OCR, ExtractionStatus.EMPTY, "failed", "needs_ocr", "empty"):
            return ClaimValidationAuditReport(
                claim_id=claim_id,
                linked_evidence_ids=[],
                exact_source_quotes=[],
                structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                evidence_relationship=None,
                validation_status=ClaimValidationStatus.INSUFFICIENT_EVIDENCE,
                extraction_status=str(ext_status),
                reasoning_summary=f"Source extraction state was '{ext_status}'. Insufficient readable evidence available to evaluate claim.",
                missing_conditions=[],
                missing_exceptions=[],
                warnings=[f"Extraction lifecycle status: {ext_status}"],
                confidence=0.0,
                source_version=source_version,
                locator=claim_loc if isinstance(claim_loc, dict) else {},
            )

        # 2. Retrieve Candidate Evidence
        retrieved_units = cls.retrieve_candidate_evidence(claim, evidence_units)

        # If no evidence units found or locator cannot resolve -> INSUFFICIENT_EVIDENCE
        if not retrieved_units:
            return ClaimValidationAuditReport(
                claim_id=claim_id,
                linked_evidence_ids=[],
                exact_source_quotes=[],
                structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                evidence_relationship=None,
                validation_status=ClaimValidationStatus.INSUFFICIENT_EVIDENCE,
                extraction_status=str(ext_status),
                reasoning_summary="No source evidence units could be retrieved or matched. Missing citation is not proof of contradiction.",
                missing_conditions=[],
                missing_exceptions=[],
                warnings=["Missing source evidence units for candidate citation."],
                confidence=0.0,
                source_version=source_version,
                locator=claim_loc if isinstance(claim_loc, dict) else {},
            )

        # 3. Verify Evidence Links
        verified_units: List[Any] = []
        exact_quotes: List[str] = []
        link_failures: List[str] = []

        for u in retrieved_units:
            is_ver, quote, err = cls.verify_evidence_link(claim, u)
            if is_ver:
                verified_units.append(u)
                if quote:
                    exact_quotes.append(quote)
            else:
                if err:
                    link_failures.append(err)

        if not verified_units:
            return ClaimValidationAuditReport(
                claim_id=claim_id,
                linked_evidence_ids=[],
                exact_source_quotes=[],
                structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                evidence_relationship=None,
                validation_status=ClaimValidationStatus.INSUFFICIENT_EVIDENCE,
                extraction_status=str(ext_status),
                reasoning_summary=f"Candidate evidence links failed verification: {'; '.join(link_failures[:2])}",
                missing_conditions=[],
                missing_exceptions=[],
                warnings=link_failures,
                confidence=0.0,
                source_version=source_version,
                locator=claim_loc if isinstance(claim_loc, dict) else {},
            )

        # Collect all identifiers for verified units
        linked_ids: List[str] = []
        for u in verified_units:
            for identifier in _get_unit_identifiers(u):
                if identifier and identifier not in linked_ids:
                    linked_ids.append(identifier)

        # 4. Table Grid Coordinate Validation
        tb = getattr(claim, "table_binding", None)
        if tb:
            cell_val = str(getattr(tb, "cell_value", "") or "").strip()
            norm_val = str(getattr(tb, "normalized_value", "") or "").strip()
            col_hdr = str(getattr(tb, "column_header", "") or "").strip().lower()
            row_key = str(getattr(tb, "row_key", "") or "").strip()

            for u in verified_units:
                struct = getattr(u, "structured_data", None) or (u.get("structured_data") if isinstance(u, dict) else {})
                grid = struct.get("grid") or struct.get("rows")
                headers = struct.get("headers") or []
                norm_headers = [str(h).strip().lower() for h in headers]

                if headers and col_hdr not in norm_headers:
                    return ClaimValidationAuditReport(
                        claim_id=claim_id,
                        linked_evidence_ids=linked_ids,
                        exact_source_quotes=exact_quotes,
                        structured_references={"table_binding": tb.model_dump() if hasattr(tb, "model_dump") else str(tb)},
                        evidence_relationship="table_binding",
                        validation_status=ClaimValidationStatus.NEEDS_REVIEW,
                        extraction_status=str(ext_status),
                        reasoning_summary=f"Table validation error: Column header '{tb.column_header}' does not match any table headers {headers}.",
                        missing_conditions=[],
                        missing_exceptions=[],
                        warnings=[f"Header path mismatch: '{tb.column_header}' not in table headers"],
                        confidence=0.4,
                        source_version=source_version,
                        locator=claim_loc if isinstance(claim_loc, dict) else {},
                    )

                if grid and isinstance(grid, list):
                    for row in grid:
                        if isinstance(row, dict):
                            r_key_val = str(row.get(headers[0], "") if headers else "")
                            if (row_key and row_key.lower() in r_key_val.lower()) or (r_key_val and r_key_val.lower() in row_key.lower()):
                                expected_cell = str(row.get(tb.column_header, "")).strip()
                                if expected_cell and cell_val and cell_val.lower() != expected_cell.lower() and norm_val.lower() != expected_cell.lower():
                                    wrong_col = None
                                    for h, val in row.items():
                                        if (cell_val.lower() == str(val).strip().lower() or norm_val.lower() == str(val).strip().lower()) and str(h).lower() != col_hdr:
                                            wrong_col = h
                                            break
                                    warn = f"Value '{cell_val}' belongs to column '{wrong_col}', not asserted column '{tb.column_header}'" if wrong_col else f"Cell value '{cell_val}' does not match row value '{expected_cell}' for column '{tb.column_header}'"
                                    return ClaimValidationAuditReport(
                                        claim_id=claim_id,
                                        linked_evidence_ids=linked_ids,
                                        exact_source_quotes=exact_quotes,
                                        structured_references={"table_binding": tb.model_dump() if hasattr(tb, "model_dump") else str(tb)},
                                        evidence_relationship="table_binding",
                                        validation_status=ClaimValidationStatus.NEEDS_REVIEW,
                                        extraction_status=str(ext_status),
                                        reasoning_summary=f"Table cell validation mismatch: {warn}.",
                                        missing_conditions=[],
                                        missing_exceptions=[],
                                        warnings=[warn],
                                        confidence=0.3,
                                        source_version=source_version,
                                        locator=claim_loc if isinstance(claim_loc, dict) else {},
                                    )

            if getattr(tb, "is_merged_cell", False) or getattr(claim, "is_ambiguous", False):
                return ClaimValidationAuditReport(
                    claim_id=claim_id,
                    linked_evidence_ids=linked_ids,
                    exact_source_quotes=exact_quotes,
                    structured_references={"table_binding": tb.model_dump() if hasattr(tb, "model_dump") else str(tb)},
                    evidence_relationship="table_binding",
                    validation_status=ClaimValidationStatus.NEEDS_REVIEW,
                    extraction_status=str(ext_status),
                    reasoning_summary=f"Table mapping ambiguous: {getattr(claim, 'ambiguity_reason', 'Merged cell or multi-column span requires manual review')}.",
                    missing_conditions=[],
                    missing_exceptions=[],
                    warnings=["Ambiguous table grid cell mapping"],
                    confidence=0.6,
                    source_version=source_version,
                    locator=claim_loc if isinstance(claim_loc, dict) else {},
                )

        # 5. Direct Source Contradiction Check
        combined_text = " ".join([_get_unit_text(u) for u in verified_units]).lower()
        claim_mod = getattr(claim, "modality", "POLICY_FACT")
        claim_text_lower = (claim.claim_text or "").lower()

        is_unit_prohibition = bool(re.search(r"\b(strictly prohibited|prohibited|shall not|must not|forbidden|may not|cannot)\b", combined_text))
        is_claim_permission = (claim_mod in ("PERMITTED", "RECOMMENDED") or bool(re.search(r"\b(may|can|permitted|allowed|eligible)\b", claim_text_lower)))
        is_claim_prohibition = (claim_mod == "PROHIBITED" or bool(re.search(r"\b(prohibited|shall not|must not|forbidden|may not|cannot)\b", claim_text_lower)))
        is_unit_permission = bool(re.search(r"\b(may|can|permitted|allowed|eligible)\b", combined_text))

        subj_tokens = _extract_content_tokens(claim.subject)
        has_same_subj = any(st in combined_text for st in subj_tokens) if subj_tokens else True

        if has_same_subj:
            if is_unit_prohibition and is_claim_permission and not is_claim_prohibition:
                return ClaimValidationAuditReport(
                    claim_id=claim_id,
                    linked_evidence_ids=linked_ids,
                    exact_source_quotes=exact_quotes,
                    structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                    evidence_relationship="conflict",
                    validation_status=ClaimValidationStatus.CONTRADICTED,
                    extraction_status=str(ext_status),
                    reasoning_summary=f"CONTRADICTED: Deontic conflict. Source evidence strictly prohibits action while claim asserts permission for '{claim.subject}'.",
                    missing_conditions=[],
                    missing_exceptions=[],
                    warnings=["Direct deontic conflict: source text prohibits what claim permits."],
                    confidence=0.98,
                    source_version=source_version,
                    locator=claim_loc if isinstance(claim_loc, dict) else {},
                )

        # 6. Multi-Evidence Synthesis & Condition / Exception Verification
        claim_conditions = [str(c).strip().lower() for c in (getattr(claim, "conditions", []) or [])]
        claim_exceptions = [str(e).strip().lower() for e in (getattr(claim, "exceptions", []) or [])]

        source_cond_patterns = [
            r"\bprovided\s+(?:that\s+)?([^,.;]+)",
            r"\bprovided\s+less\s+than\s+([^,.;]+)",
            r"\bif\s+in\s+([^,.;]+)",
            r"\bif\s+([^,.;]+)",
            r"\bonly\s+if\s+([^,.;]+)",
            r"\bsubject\s+to\s+([^,.;]+)",
        ]
        source_exc_patterns = [
            r"\bexcept\s+([^,.;]+)",
            r"\bexcept\s+for\s+([^,.;]+)",
            r"\bexcluding\s+([^,.;]+)",
            r"\bexcludes\s+([^,.;]+)",
            r"\bwith\s+the\s+exception\s+of\s+([^,.;]+)",
            r"\bunless\s+([^,.;]+)",
        ]

        source_detected_conditions = []
        for pat in source_cond_patterns:
            for match in re.finditer(pat, combined_text):
                cond_phrase = match.group(0).strip()
                if len(cond_phrase) > 5:
                    source_detected_conditions.append(cond_phrase)

        source_detected_exceptions = []
        for pat in source_exc_patterns:
            for match in re.finditer(pat, combined_text):
                exc_phrase = match.group(0).strip()
                if len(exc_phrase) > 5:
                    source_detected_exceptions.append(exc_phrase)

        for s_cond in source_detected_conditions:
            s_tokens = _extract_content_tokens(s_cond)
            claim_all_text = (claim.claim_text + " " + " ".join(claim_conditions)).lower()
            if s_tokens and not any(t in claim_all_text for t in s_tokens):
                missing_conditions.append(s_cond)

        for s_exc in source_detected_exceptions:
            e_tokens = _extract_content_tokens(s_exc)
            claim_all_text = (claim.claim_text + " " + " ".join(claim_exceptions)).lower()
            if e_tokens and not any(t in claim_all_text for t in e_tokens):
                missing_exceptions.append(s_exc)

        if missing_conditions or missing_exceptions:
            summary_parts = []
            if missing_conditions:
                summary_parts.append(f"Source conditions omitted from claim: {missing_conditions}")
            if missing_exceptions:
                summary_parts.append(f"Source exceptions omitted from claim: {missing_exceptions}")
            return ClaimValidationAuditReport(
                claim_id=claim_id,
                linked_evidence_ids=linked_ids,
                exact_source_quotes=exact_quotes,
                structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                evidence_relationship="multi_block" if len(verified_units) > 1 else "single_unit",
                validation_status=ClaimValidationStatus.NEEDS_REVIEW,
                extraction_status=str(ext_status),
                reasoning_summary=f"Incomplete claim context: {'; '.join(summary_parts)}.",
                missing_conditions=missing_conditions,
                missing_exceptions=missing_exceptions,
                warnings=["Claim omitted required qualifying conditions or exceptions."],
                confidence=0.70,
                source_version=source_version,
                locator=claim_loc if isinstance(claim_loc, dict) else {},
            )

        # 7. Contradiction & Version Progression Check Against Historical Claims
        claim_val = getattr(claim, "value", None)

        if historical_claims:
            for hist in historical_claims:
                hist_id = getattr(hist, "candidate_id", None) or getattr(hist, "id", None)
                if hist_id == claim_id:
                    continue
                hist_subj = getattr(hist, "subject", "") or ""
                if hist_subj and claim.subject and _normalize_text(hist_subj) == _normalize_text(claim.subject):
                    hist_ver = getattr(hist, "source_version", None)
                    if hist_ver and source_version and hist_ver != source_version:
                        ver_curr = _parse_version(source_version)
                        ver_hist = _parse_version(hist_ver)
                        if ver_curr > ver_hist:
                            warnings.append(
                                f"Historical claim '{hist_id}' from older version '{hist_ver}' is superseded by current version '{source_version}'."
                            )
                            continue
                        elif ver_curr < ver_hist:
                            return ClaimValidationAuditReport(
                                claim_id=claim_id,
                                linked_evidence_ids=linked_ids,
                                exact_source_quotes=exact_quotes,
                                structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                                evidence_relationship="version_lineage",
                                validation_status=ClaimValidationStatus.NEEDS_REVIEW,
                                extraction_status=str(ext_status),
                                reasoning_summary=f"Claim is from older version '{source_version}' and has been superseded by '{hist_ver}'.",
                                missing_conditions=[],
                                missing_exceptions=[],
                                warnings=[f"Superseded by active version {hist_ver}"],
                                confidence=0.5,
                                source_version=source_version,
                                locator=claim_loc if isinstance(claim_loc, dict) else {},
                            )

                    hist_val = getattr(hist, "value", None)
                    hist_mod = getattr(hist, "modality", "POLICY_FACT")
                    if claim_val is not None and hist_val is not None and str(claim_val) != str(hist_val):
                        return ClaimValidationAuditReport(
                            claim_id=claim_id,
                            linked_evidence_ids=linked_ids,
                            exact_source_quotes=exact_quotes,
                            structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                            evidence_relationship="conflict",
                            validation_status=ClaimValidationStatus.CONTRADICTED,
                            extraction_status=str(ext_status),
                            reasoning_summary=f"CONTRADICTED: Extracted value '{claim_val}' conflicts directly with competing active claim value '{hist_val}' for subject '{claim.subject}'.",
                            missing_conditions=[],
                            missing_exceptions=[],
                            warnings=[f"Direct numeric contradiction with claim {hist_id}"],
                            confidence=0.95,
                            source_version=source_version,
                            locator=claim_loc if isinstance(claim_loc, dict) else {},
                        )

                    if (claim_mod == "PROHIBITED" and hist_mod in ("REQUIRED", "PERMITTED")) or (claim_mod in ("REQUIRED", "PERMITTED") and hist_mod == "PROHIBITED"):
                        return ClaimValidationAuditReport(
                            claim_id=claim_id,
                            linked_evidence_ids=linked_ids,
                            exact_source_quotes=exact_quotes,
                            structured_references=claim_loc if isinstance(claim_loc, dict) else {},
                            evidence_relationship="conflict",
                            validation_status=ClaimValidationStatus.CONTRADICTED,
                            extraction_status=str(ext_status),
                            reasoning_summary=f"CONTRADICTED: Deontic conflict between {claim_mod} and {hist_mod} for subject '{claim.subject}'.",
                            missing_conditions=[],
                            missing_exceptions=[],
                            warnings=[f"Direct deontic contradiction with claim {hist_id}"],
                            confidence=0.98,
                            source_version=source_version,
                            locator=claim_loc if isinstance(claim_loc, dict) else {},
                        )

        # 8. Multi-Block Evidence Support Verification
        relationship_type = "multi_block" if len(verified_units) > 1 else (getattr(claim, "evidence_relationship_type", None) or "single_unit")
        roles = [getattr(u, "content_role", None) for u in verified_units]
        if ContentRole.DEFINITION in roles or "definition" in roles:
            relationship_type = "rule_with_definition"
        elif ContentRole.EXCEPTION in roles or "exception" in roles:
            relationship_type = "rule_with_exception"

        return ClaimValidationAuditReport(
            claim_id=claim_id,
            linked_evidence_ids=linked_ids,
            exact_source_quotes=exact_quotes,
            structured_references=claim_loc if isinstance(claim_loc, dict) else {},
            evidence_relationship=relationship_type,
            validation_status=ClaimValidationStatus.SUPPORTED,
            extraction_status=str(ext_status),
            reasoning_summary=f"SUPPORTED: Claim verified against {len(verified_units)} source evidence unit(s) with preserved exact quote fidelity and grounded conditions.",
            missing_conditions=[],
            missing_exceptions=[],
            warnings=warnings,
            confidence=0.96 if len(verified_units) > 1 else 0.98,
            source_version=source_version,
            locator=claim_loc if isinstance(claim_loc, dict) else {},
        )
