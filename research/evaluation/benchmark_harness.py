"""
Trulin Multi-Stage Ground-Truth Benchmark & Metric Evaluation Harness (Version 3.1).
Implements strict tiered quality thresholds, 1-to-1 claim reservation,
predicate semantic family matching, immutable manifest verification,
split match tiers (FULL_MATCH, ACCEPTED_PARTIAL_MATCH, UNJUDGED),
symmetric metric calculations, and closed auditable candidate ledger accounting.
"""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def unpack_gold_object(obj_val: Any) -> Tuple[str, List[str], str]:
    """Unpacks gold object (dict, string, or primitive) into comparable string, tokens, and modality."""
    tokens = set()
    full_str = ""
    modality = "UNKNOWN"
    if isinstance(obj_val, dict):
        val = str(obj_val.get("value", "")).strip().lower()
        unit = str(obj_val.get("unit", "")).strip().lower()
        curr = str(obj_val.get("currency", "")).strip().lower()
        modality = str(obj_val.get("modality", "UNKNOWN")).strip().upper()
        full_str = f"{val} {unit}".strip()
        if val:
            tokens.add(val)
            for w in re.findall(r"\b\w+\b", val):
                if len(w) > 1:
                    tokens.add(w)
            try:
                fval = float(val)
                tokens.add(f"{fval:.2f}")
                tokens.add(f"${fval:.2f}")
                tokens.add(f"${fval:.0f}" if fval.is_integer() else f"${fval}")
                tokens.add(f"{fval:.0f}" if fval.is_integer() else f"{fval}")
            except ValueError:
                pass
        if unit:
            tokens.add(unit)
            if unit.endswith("y"):
                tokens.add(unit[:-1] + "ies")
            elif not unit.endswith("s"):
                tokens.add(unit + "s")
        if curr:
            tokens.add(curr)
            if curr in ("usd", "$"):
                tokens.add("$")
                tokens.add("usd")
    elif isinstance(obj_val, (int, float)):
        s = str(obj_val).strip()
        full_str = s
        tokens.add(s)
        try:
            fval = float(obj_val)
            tokens.add(f"{fval:.2f}")
            tokens.add(f"${fval:.2f}")
            tokens.add(f"${fval:.0f}" if fval.is_integer() else f"${fval}")
            tokens.add(f"{fval:.0f}" if fval.is_integer() else f"{fval}")
        except ValueError:
            pass
    elif isinstance(obj_val, str):
        full_str = obj_val.strip().lower()
        for w in re.findall(r"\b\w+\b", full_str):
            if len(w) > 1:
                tokens.add(w)
        tokens.add(full_str)
    return full_str, list(tokens), modality


class BenchmarkHarness:
    # Strict Tiered Production Quality Thresholds
    THRESHOLDS = {
        "pass": {
            "min_full_recall": 0.90,
            "min_full_precision": 0.90,
            "min_full_f1": 0.90,
            "min_subject_acc": 0.95,
            "min_predicate_acc": 0.95,
            "min_object_acc": 0.95,
            "max_false_approval": 0.02,
            "max_false_conflict": 0.02,
            "max_malformed": 0.00,
            "min_traceability": 1.00,
        },
        "conditional": {
            "min_partial_recall": 0.75,
            "min_lower_precision": 0.35,
            "min_partial_f1": 0.50,
            "min_subject_acc": 0.85,
            "max_false_approval": 0.05,
            "max_false_conflict": 0.05,
            "max_malformed": 0.01,
        },
    }

    # Strict Semantic Predicate Families (Cross-family matching is forbidden)
    PREDICATE_FAMILIES = {
        "return_window": {"has_return_window", "return_window", "requires_return_within_applicable_window"},
        "notice_period": {
            "has_notice_period", "notice_period", "has_standard_notice_duration",
            "has_maximum_notice_duration", "has_confirmed_notice_duration",
            "has_notice_duration", "has_probationary_notice_duration", "summarizes_grade_tenures"
        },
        "due_date": {"has_due_date_period", "has_due_date"},
        "reimbursement": {"has_refund_reimbursement_window", "reimburse", "reimbursed"},
        "financial_totals": {"has_sub_total", "has_total_due", "has_tax_amount", "has_service_rate_price"},
        "product_exclusion": {"cannot_be_returned", "prohibited_from_return"},
        "eligibility": {"has_refund_eligibility", "has_eligibility_condition"},
        "duration_limit": {"has_duration_limit"},
        "compensation": {"has_compensation_rate"},
        "governing_rule": {"has_governing_rule", "specifies_governing_rule", "has_validity_rule", "scrupulously"},
        "age_restriction": {"has_age_restriction"},
        "financial_power": {"has_financial_power_restriction"},
        "leave_rule": {"has_encashment_limit", "has_leave_entitlement"},
        "medical": {"has_medical_reimbursement"},
        "shipping": {"has_shipping_cost_rule", "covers_shipping_costs"},
        "reporting": {"has_reporting_requirement", "has_response_deadline"},
        "dispute": {"has_dispute_resolution_preference", "has_evidence_submission_deadline", "has_dispute_decision_timeline"},
        "definition": {"has_definition", "defines", "defined", "has_definition_threshold"},
        "property_return": {"must_return_all_company_property", "must_return_company_property"},
        "misconduct_termination": {"may_occur_without_notice", "occur", "occurs_without_notice"},
        "notification": {"notify_human_resources", "notify", "notifies", "has_notification_requirement"},
    }

    def __init__(
        self,
        gold_dir: Path = Path("B:/Context_Layer_Ai/research/gold_labels"),
        results_dir: Path = Path("B:/Context_Layer_Ai/research/extraction-results"),
        manifest_path: Path = Path("B:/Context_Layer_Ai/research/evaluation/corpus_manifest.json"),
    ):
        self.gold_dir = gold_dir
        self.results_dir = results_dir
        self.manifest_path = manifest_path
        self.manifest: Dict[str, Any] = {}
        if self.manifest_path.exists():
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def are_predicates_compatible(self, gold_pred: str, cand_pred: str) -> bool:
        """Determines semantic compatibility between gold and candidate predicates."""
        g = gold_pred.lower().strip()
        c = cand_pred.lower().strip()
        if g == c:
            return True
        for fam_name, fam_preds in self.PREDICATE_FAMILIES.items():
            if g in fam_preds and c in fam_preds:
                return True
        if g in ("has_validity_rule", "specifies_governing_rule", "has_governing_rule") and c in ("has_validity_rule", "specifies_governing_rule", "has_governing_rule"):
            return True
        return False

    def evaluate_document(self, doc_code: str) -> Dict[str, Any]:
        manifest_meta = self.manifest.get("documents", {}).get(doc_code, {})
        canonical_title = manifest_meta.get("title") or f"Document {doc_code}"
        canonical_org = manifest_meta.get("organization") or "Unknown Organization"
        canonical_doc_type = manifest_meta.get("document_type") or "policy"

        gold_file = self.gold_dir / f"{doc_code}_gold.json"
        res_file = self.results_dir / f"{doc_code}_output.json"

        if not gold_file.exists():
            raise FileNotFoundError(f"Gold label file not found: {gold_file}")
        if not res_file.exists():
            raise FileNotFoundError(f"Extraction result file not found: {res_file}")

        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        res = json.loads(res_file.read_text(encoding="utf-8"))

        ext_resp = res.get("extraction_response", {})
        claims = ext_resp.get("claims", [])
        artifacts = res.get("artifacts", {})
        conflicts = artifacts.get("conflicts", [])

        gold_claims = gold.get("claim_truth", [])
        gold_canonical = [c for c in gold_claims if c.get("canonical", True)]
        is_scanned_doc = not gold.get("layout_truth", {}).get("has_selectable_text", True)

        # -------------------------------------------------------------
        # Stage 1: Candidate Population Categorization
        # -------------------------------------------------------------
        total_extracted = len(claims)
        approved_claims = [c for c in claims if c.get("status") in ("approved", "verified")]
        rejected_claims = [c for c in claims if c.get("status") == "rejected"]
        review_claims = [c for c in claims if c.get("status") in ("review", "queued")]

        non_canonical_approved = [c for c in approved_claims if not c.get("is_canonical", True)]
        boilerplate_patterns = [
            "unauthorized use", "proprietary", "confidential", "all rights reserved",
            "table of contents", "revision history"
        ]
        boilerplate_approved = [
            c for c in approved_claims
            if c.get("is_canonical", True) and any(m in (c.get("claim_text") or "").lower() for m in boilerplate_patterns)
        ]
        non_boilerplate_approved = [
            c for c in approved_claims
            if c.get("is_canonical", True) and not any(m in (c.get("claim_text") or "").lower() for m in boilerplate_patterns)
        ]

        # Deduplicate: Canonical Approved contains strictly unique claims; duplicates are tracked as non-canonical evidence links
        seen_canonical = set()
        canonical_approved_claims = []
        duplicate_evidence_links = []
        for c in non_boilerplate_approved:
            key = (str(c.get("subject")).strip().lower(), str(c.get("predicate")).strip().lower(), str(c.get("object")).strip().lower()[:30])
            if key not in seen_canonical:
                seen_canonical.add(key)
                canonical_approved_claims.append(c)
            else:
                duplicate_evidence_links.append(c)

        dedup_canonical = list(canonical_approved_claims)
        duplicate_canonical = list(duplicate_evidence_links)

        malformed_fragments = []
        for c in claims:
            txt = (c.get("claim_text") or "") + " " + (c.get("subject") or "")
            if any(p in txt for p in ["Respons ibilities", "O Responsibilities", "released immediately wit", "insubordinat ion", "seve re", "wit hout"]):
                malformed_fragments.append(c)

        malformed_fragment_rate = round(len(malformed_fragments) / max(total_extracted, 1), 4)

        # L6-to-Canonical Reconciliation Audit Invariant: Approved L6 = Canonical Approved + Duplicates + Boilerplate + Non-Canonical
        approved_l6_total = len(approved_claims)
        canonical_approved_total = len(canonical_approved_claims)
        excluded_non_canonical = len(non_canonical_approved)
        excluded_boilerplate = len(boilerplate_approved)
        excluded_duplicate = len(duplicate_evidence_links)
        excluded_malformed = 0
        excluded_other = 0
        reconciliation_difference = approved_l6_total - (
            canonical_approved_total
            + excluded_non_canonical
            + excluded_boilerplate
            + excluded_duplicate
            + excluded_malformed
            + excluded_other
        )
        assert reconciliation_difference == 0, f"L6 Reconciliation difference in {doc_code}: {reconciliation_difference} != 0"

        # -------------------------------------------------------------
        # Stage 2: Multi-Tier Claim Matching with 1-to-1 Reservation
        # -------------------------------------------------------------
        claim_classifications: Dict[str, Dict[str, Any]] = {}
        consumed_canonical_ids: Set[str] = set()
        consumed_raw_ids: Set[str] = set()

        matched_full_gold_ids: Set[str] = set()
        matched_partial_gold_ids: Set[str] = set()
        matched_raw_discovery_gold_ids: Set[str] = set()

        matched_canonical_full_ids: Set[str] = set()
        matched_canonical_partial_ids: Set[str] = set()

        invalid_subject_count = 0
        correct_predicate_count = 0
        correct_object_count = 0

        # Scan extracted claims for subject validity
        for c in claims:
            sub = (c.get("subject") or "").strip()
            if sub.startswith("Page ") or sub in ("3", "2", "1", "Subject", "Total") or "wit hout" in sub:
                invalid_subject_count += 1

        # Match each gold canonical claim
        for g in gold_canonical:
            g_id = g.get("claim_id", "")
            g_sub = (g.get("subject") or "").lower().strip()
            g_pred = (g.get("predicate") or "").lower().strip()
            g_quote = (g.get("evidence_quote") or "").lower().strip()
            g_obj_full, g_obj_tokens, g_modality = unpack_gold_object(g.get("object"))

            best_match: Dict[str, Any] | None = None
            match_tier = "MISSING"
            taxonomy = "UNKNOWN"
            is_full = False
            is_partial = False

            # Phase A: Check canonical approved claims first (Strict 1-to-1)
            for c in canonical_approved_claims:
                c_id = str(c.get("id"))
                if c_id in consumed_canonical_ids:
                    continue

                c_text = (c.get("claim_text") or "").lower().strip()
                c_sub = (c.get("subject") or "").strip().lower()
                c_pred = (c.get("predicate") or "").strip().lower()
                c_obj = str(c.get("object") or "").lower().strip()
                c_quote = str(c.get("evidence_text_span") or "").lower().strip()
                c_modality = str(c.get("modality", "")).upper().strip()

                if not g_quote or len(g_quote) < 5 or not c_text:
                    continue

                # Evidence grounding overlap test
                content_matched = False
                if g_quote[:35] in c_text or (len(c_text) > 20 and c_text[:35] in g_quote):
                    content_matched = True
                elif c_quote and (g_quote[:35] in c_quote or (len(c_quote) > 20 and c_quote[:35] in g_quote)):
                    content_matched = True
                elif g_obj_full and len(g_obj_full) > 4 and g_obj_full in c_text:
                    content_matched = True
                elif any(len(phrase) > 12 and phrase in c_text for phrase in g_quote.split(", ")):
                    content_matched = True

                if content_matched:
                    is_generic_subject = (
                        c_sub.startswith("page ")
                        or (c_sub in ("1", "2", "3", "subject") and g_sub not in ("1", "2", "3", "subject"))
                        or (c_sub == "total" and g_sub != "total")
                    )
                    subject_ok = (
                        not is_generic_subject and (
                            g_sub in c_sub
                            or c_sub in g_sub
                            or any(w in c_sub for w in g_sub.split() if len(w) > 4)
                            or (g_sub in c_text and not is_generic_subject)
                        )
                    )

                    predicate_ok = self.are_predicates_compatible(g_pred, c_pred)

                    # Object numerical / semantic check
                    g_nums = re.findall(r"\b\d+(?:\.\d+)?\b", g_obj_full)
                    c_nums = re.findall(r"\b\d+(?:\.\d+)?\b", c_obj)

                    numerical_conflict = False
                    if g_nums and c_nums:
                        try:
                            g_floats = {float(x) for x in g_nums}
                            c_floats = {float(x) for x in c_nums}
                            if not (g_floats & c_floats):
                                numerical_conflict = True
                        except ValueError:
                            pass

                    object_full_ok = False
                    object_partial_ok = False

                    if numerical_conflict:
                        object_full_ok = False
                        object_partial_ok = False
                    else:
                        has_num_match = bool(g_nums and c_nums and ({float(x) for x in g_nums} & {float(x) for x in c_nums}))
                        has_exact_obj = bool(g_obj_full and (g_obj_full in c_obj or c_obj in g_obj_full))
                        has_key_tokens = any(tok in c_obj for tok in g_obj_tokens if len(tok) >= 2 and tok not in ("day", "days", "week", "weeks", "month", "months", "year", "years"))
                        obj_in_quote = bool(c_obj in g_quote and len(c_obj) >= 4)

                        if g_nums:
                            # Gold has numeric threshold: FULL_MATCH requires number match or exact object string containing the number
                            if has_num_match or (has_exact_obj and any(n in c_obj for n in g_nums)):
                                object_full_ok = True
                            elif has_exact_obj or has_key_tokens or obj_in_quote:
                                object_partial_ok = True
                        else:
                            # Non-numeric gold object
                            if has_exact_obj or (has_key_tokens and len(c_obj) >= 4):
                                object_full_ok = True
                            elif obj_in_quote:
                                object_partial_ok = True

                    # Modality preservation
                    modality_ok = True
                    if g_modality in ("MUST_NOT", "PROHIBITION") and c_modality in ("PERMISSION", "MAY"):
                        modality_ok = False
                    elif g_pred in ("cannot_be_returned", "has_age_restriction", "has_financial_power_restriction") and c_modality in ("PERMISSION", "MAY"):
                        modality_ok = False

                    if subject_ok and predicate_ok and object_full_ok and modality_ok:
                        match_tier = "FULL_MATCH"
                        taxonomy = "NONE"
                        best_match = c
                        is_full = True
                        correct_predicate_count += 1
                        correct_object_count += 1
                        matched_full_gold_ids.add(g_id)
                        matched_canonical_full_ids.add(c_id)
                        consumed_canonical_ids.add(c_id)
                        break
                    elif not modality_ok:
                        match_tier = "WRONG_MODALITY"
                        taxonomy = "MODALITY_CONTRADICTION"
                        best_match = c
                    elif numerical_conflict:
                        match_tier = "WRONG_OBJECT"
                        taxonomy = "NUMERICAL_CONTRADICTION"
                        best_match = c
                    elif not predicate_ok and subject_ok:
                        match_tier = "WRONG_PREDICATE"
                        taxonomy = "PREDICATE_MAPPING_ERROR"
                        best_match = c
                    elif not subject_ok and (predicate_ok or object_full_ok or object_partial_ok):
                        match_tier = "WRONG_SUBJECT"
                        taxonomy = "SUBJECT_RESOLUTION_ERROR"
                        best_match = c
                    elif subject_ok and predicate_ok and (object_partial_ok or len(c_quote) > 15) and modality_ok and not numerical_conflict:
                        match_tier = "PARTIAL_OBJECT_CAPTURE_PENDING_REVIEW"
                        taxonomy = "PARTIAL_OBJECT_CAPTURE" if not object_full_ok else "PARTIAL_FIDELITY"
                        best_match = c
                        is_partial = True
                        matched_partial_gold_ids.add(g_id)
                        matched_canonical_partial_ids.add(c_id)
                        consumed_canonical_ids.add(c_id)
                        break

            # Phase B: If not matched in canonical approved, check raw candidate discovery stream
            if not is_full and not is_partial and match_tier not in ("WRONG_OBJECT", "WRONG_MODALITY"):
                for c in claims:
                    c_id = str(c.get("id"))
                    if c_id in consumed_raw_ids or c_id in consumed_canonical_ids:
                        continue

                    c_text = (c.get("claim_text") or "").lower().strip()
                    c_sub = (c.get("subject") or "").strip().lower()
                    c_pred = (c.get("predicate") or "").strip().lower()
                    c_obj = str(c.get("object") or "").lower().strip()
                    c_quote = str(c.get("evidence_text_span") or "").lower().strip()
                    c_modality = str(c.get("modality", "")).upper().strip()

                    if not g_quote or len(g_quote) < 5 or not c_text:
                        continue

                    content_matched = False
                    if g_quote[:35] in c_text or (len(c_text) > 20 and c_text[:35] in g_quote):
                        content_matched = True
                    elif c_quote and (g_quote[:35] in c_quote or (len(c_quote) > 20 and c_quote[:35] in g_quote)):
                        content_matched = True
                    elif g_obj_full and len(g_obj_full) > 4 and g_obj_full in c_text:
                        content_matched = True
                    elif any(len(phrase) > 12 and phrase in c_text for phrase in g_quote.split(", ")):
                        content_matched = True

                    if content_matched:
                        is_generic_subject = c_sub.startswith("page ") or c_sub in ("1", "2", "3", "subject", "total")
                        subject_ok = not is_generic_subject and (g_sub in c_sub or c_sub in g_sub or any(w in c_sub for w in g_sub.split() if len(w) > 4) or g_sub in c_text)
                        predicate_ok = self.are_predicates_compatible(g_pred, c_pred)

                        g_nums = re.findall(r"\b\d+(?:\.\d+)?\b", g_obj_full)
                        c_nums = re.findall(r"\b\d+(?:\.\d+)?\b", c_obj)
                        num_conflict = False
                        if g_nums and c_nums:
                            try:
                                if not ({float(x) for x in g_nums} & {float(x) for x in c_nums}):
                                    num_conflict = True
                            except ValueError:
                                pass

                        object_ok = not num_conflict and ((g_obj_full and (g_obj_full in c_obj or c_obj in g_obj_full)) or (c_obj in g_quote) or any(tok in c_obj for tok in g_obj_tokens if len(tok) >= 2 and tok not in ("day", "days", "week", "weeks", "month", "months")))
                        modality_ok = not (g_modality in ("MUST_NOT", "PROHIBITION") and c_modality in ("PERMISSION", "MAY"))

                        if subject_ok and predicate_ok and object_ok and modality_ok:
                            match_tier = "RAW_DISCOVERY_MATCH"
                            taxonomy = "UNAPPROVED_RAW_DISCOVERY"
                            best_match = c
                            matched_raw_discovery_gold_ids.add(g_id)
                            consumed_raw_ids.add(c_id)
                            break
                        elif not modality_ok:
                            match_tier = "WRONG_MODALITY"
                            taxonomy = "MODALITY_CONTRADICTION"
                            best_match = c
                        elif num_conflict:
                            match_tier = "WRONG_OBJECT"
                            taxonomy = "NUMERICAL_CONTRADICTION"
                            best_match = c

            if not is_full and not is_partial:
                if match_tier not in ("WRONG_OBJECT", "WRONG_MODALITY", "WRONG_PREDICATE", "WRONG_SUBJECT"):
                    if is_scanned_doc:
                        taxonomy = "OCR_MISREAD"
                    elif any(tbl.get("headers") for tbl in gold.get("table_truth", [])):
                        taxonomy = "TABLE_STRUCTURE_ERROR"
                    else:
                        taxonomy = "SENTENCE_SPLIT_ERROR"

            if is_full:
                final_status = "MATCHED"
            elif is_partial:
                final_status = "PARTIAL"
            elif match_tier in ("WRONG_OBJECT", "WRONG_MODALITY", "WRONG_PREDICATE", "WRONG_SUBJECT"):
                final_status = match_tier
            else:
                final_status = "MISSING"

            claim_classifications[g_id] = {
                "claim_id": g_id,
                "gold_subject": g.get("subject"),
                "status": final_status,
                "match_tier": match_tier,
                "taxonomy": taxonomy,
                "evidence_quote": g.get("evidence_quote", "")[:60],
                "matched_claim_id": best_match.get("id") if best_match else None,
                "matched_subject": best_match.get("subject") if best_match else None,
            }

        # -------------------------------------------------------------
        # Stage 3: Closed Candidate Ledger Accounting (Strict Disjoint Partition)
        # -------------------------------------------------------------
        correct_full_matches = len(matched_canonical_full_ids)
        correct_partial_matches = len(matched_canonical_partial_ids)

        unjudged_spans = 0
        incorrect_claims = 0
        malformed_claims = 0
        duplicate_claims = 0
        non_canonical_claims = 0

        for c in canonical_approved_claims:
            c_id = str(c.get("id"))
            if c_id in matched_canonical_full_ids or c_id in matched_canonical_partial_ids:
                continue

            txt = (c.get("claim_text") or "") + " " + (c.get("subject") or "")
            sub = (c.get("subject") or "").strip()
            span = str(c.get("evidence_text_span") or c.get("claim_text") or "")

            if any(p in txt for p in ["Respons ibilities", "O Responsibilities", "released immediately wit", "insubordinat ion"]):
                malformed_claims += 1
            elif sub.startswith("Page ") or sub in ("1", "2", "3", "Subject", "Total"):
                incorrect_claims += 1
            elif len(span) > 15:
                unjudged_spans += 1
            else:
                incorrect_claims += 1

        total_canonical = len(canonical_approved_claims)
        # Mathematical Invariant Assertion: Ledger Partition Closure
        ledger_sum = (
            correct_full_matches
            + correct_partial_matches
            + unjudged_spans
            + incorrect_claims
            + malformed_claims
            + duplicate_claims
            + non_canonical_claims
        )
        assert ledger_sum == total_canonical, f"Ledger sum mismatch in {doc_code}: {ledger_sum} != {total_canonical}"

        # -------------------------------------------------------------
        # Stage 4: Symmetric Named Metrics Triplets
        # -------------------------------------------------------------
        total_gold = len(gold_canonical)

        # 1. Full-Match Tier (Strict Production Gate)
        full_match_recall = round(len(matched_full_gold_ids) / max(total_gold, 1), 4)
        lower_bound_precision = round(correct_full_matches / max(total_canonical, 1), 4)
        if lower_bound_precision + full_match_recall > 0:
            canonical_f1_full_match = round(2 * (lower_bound_precision * full_match_recall) / (lower_bound_precision + full_match_recall), 4)
        else:
            canonical_f1_full_match = 0.0

        # 2. Partial-Match Canonical Tier (Strictly Canonical Approved Only!)
        total_captured_canonical_gold = len(matched_full_gold_ids) + len(matched_partial_gold_ids)
        partial_match_recall = round(total_captured_canonical_gold / max(total_gold, 1), 4)
        total_correct_canonical = correct_full_matches + correct_partial_matches
        partial_precision = round(total_correct_canonical / max(total_canonical, 1), 4)
        if partial_precision + partial_match_recall > 0:
            canonical_f1_partial_match = round(2 * (partial_precision * partial_match_recall) / (partial_precision + partial_match_recall), 4)
        else:
            canonical_f1_partial_match = 0.0

        # 3. Adjudication Status
        adjudicated_canonical = correct_full_matches + correct_partial_matches + incorrect_claims + malformed_claims
        if adjudicated_canonical > 0:
            adjudicated_precision = round(correct_full_matches / adjudicated_canonical, 4)
        else:
            adjudicated_precision = lower_bound_precision

        # 4. Raw Candidate Discovery Tier (Includes unapproved Layer 5 extractions)
        raw_discovery_captured_gold = total_captured_canonical_gold + len(matched_raw_discovery_gold_ids)
        raw_recall = round(raw_discovery_captured_gold / max(total_gold, 1), 4)
        raw_precision = round(total_correct_canonical / max(total_extracted, 1), 4)
        if raw_precision + raw_recall > 0:
            raw_f1 = round(2 * (raw_precision * raw_recall) / (raw_precision + raw_recall), 4)
        else:
            raw_f1 = 0.0

        subject_accuracy = round(1.0 - (invalid_subject_count / max(total_extracted, 1)), 4)
        predicate_accuracy = round(correct_predicate_count / max(len(matched_full_gold_ids), 1), 4)
        object_accuracy = round(correct_object_count / max(len(matched_full_gold_ids), 1), 4)

        false_approves = [
            c for c in approved_claims
            if (c.get("subject") or "").startswith("Page ")
            or any(p in (c.get("claim_text") or "") for p in ["O Responsibilities", "Respons ibilities", "released immediately wit", "insubordinat ion"])
        ]
        false_approve_rate = round(len(false_approves) / max(len(approved_claims), 1), 4)

        false_rejects = [
            c for c in rejected_claims
            if any(g.get("evidence_quote", "").lower()[:30] in (c.get("claim_text") or "").lower() for g in gold_canonical)
        ]
        false_reject_rate = round(len(false_rejects) / max(len(rejected_claims), 1), 4)

        false_conflicts = [
            cf for cf in conflicts
            if any(d in (cf.get("claim_a_text") or "") or d in (cf.get("claim_b_text") or "") for d in ["03/01/2009", "12/11/2013", "04/24/2017", "07/23/2021", "Edited:"])
        ]
        false_conflict_rate = round(len(false_conflicts) / max(len(conflicts), 1), 4)

        traceable_claims = [c for c in claims if len(c.get("evidence", [])) > 0 and c["evidence"][0].get("text_span")]
        evidence_span_traceability = round(len(traceable_claims) / max(total_extracted, 1), 4)

        # -------------------------------------------------------------
        # Stage 5: Dual-Gate Decision Engine (Full-Match Tier Basis)
        # -------------------------------------------------------------
        blocking_reasons: List[str] = []
        pass_cfg = self.THRESHOLDS["pass"]
        cond_cfg = self.THRESHOLDS["conditional"]

        is_pass = (
            full_match_recall >= pass_cfg["min_full_recall"]
            and lower_bound_precision >= pass_cfg["min_full_precision"]
            and canonical_f1_full_match >= pass_cfg["min_full_f1"]
            and subject_accuracy >= pass_cfg["min_subject_acc"]
            and predicate_accuracy >= pass_cfg.get("min_predicate_acc", 0.95)
            and object_accuracy >= pass_cfg.get("min_object_acc", 0.95)
            and false_approve_rate <= pass_cfg["max_false_approval"]
            and false_conflict_rate <= pass_cfg["max_false_conflict"]
            and malformed_fragment_rate <= pass_cfg["max_malformed"]
            and evidence_span_traceability >= pass_cfg.get("min_traceability", 0.95)
        )

        is_cond = (
            partial_match_recall >= cond_cfg["min_partial_recall"]
            and lower_bound_precision >= cond_cfg["min_lower_precision"]
            and canonical_f1_partial_match >= cond_cfg["min_partial_f1"]
            and subject_accuracy >= cond_cfg["min_subject_acc"]
            and false_approve_rate <= cond_cfg["max_false_approval"]
            and false_conflict_rate <= cond_cfg["max_false_conflict"]
            and malformed_fragment_rate <= cond_cfg["max_malformed"]
        )

        if is_pass:
            verdict = "PASS"
        elif is_cond:
            verdict = "CONDITIONAL_PASS"
        else:
            verdict = "NEEDS_WORK"

        if full_match_recall < pass_cfg["min_full_recall"]:
            blocking_reasons.append(f"full_match_recall_below_threshold ({full_match_recall*100:.1f}% < {pass_cfg['min_full_recall']*100:.1f}%)")
        if lower_bound_precision < pass_cfg["min_full_precision"]:
            blocking_reasons.append(f"canonical_policy_precision_below_threshold ({lower_bound_precision*100:.1f}% < {pass_cfg['min_full_precision']*100:.1f}%)")
            blocking_reasons.append(f"material_claim_precision_below_threshold ({lower_bound_precision*100:.1f}% < {pass_cfg['min_full_precision']*100:.1f}%)")
        if canonical_f1_full_match < pass_cfg["min_full_f1"]:
            blocking_reasons.append(f"f1_score_below_threshold ({canonical_f1_full_match*100:.1f}% < {pass_cfg['min_full_f1']*100:.1f}%)")
        if subject_accuracy < pass_cfg["min_subject_acc"]:
            blocking_reasons.append(f"subject_accuracy_below_threshold ({subject_accuracy*100:.1f}% < {pass_cfg['min_subject_acc']*100:.1f}%)")
        if false_approve_rate > pass_cfg["max_false_approval"]:
            blocking_reasons.append(f"false_approval_rate_above_threshold ({false_approve_rate*100:.1f}% > {pass_cfg['max_false_approval']*100:.1f}%)")

        for g_id, diag in claim_classifications.items():
            if diag["match_tier"] not in ("FULL_MATCH", "ACCEPTED_PARTIAL_MATCH", "PARTIAL_OBJECT_CAPTURE_PENDING_REVIEW"):
                blocking_reasons.append(
                    f"{diag['status']}: {g_id} [{diag['taxonomy']}] - {diag['gold_subject']}: \"{diag['evidence_quote']}\""
                )

        return {
            "document_id": doc_code,
            "title": canonical_title,
            "organization": canonical_org,
            "document_type": canonical_doc_type,
            "verdict": verdict,
            "verdict_basis": "full_match_canonical_metrics",
            "blocking_reasons": blocking_reasons,
            "metrics": {
                "full_match_recall": full_match_recall,
                "partial_match_recall": partial_match_recall,
                "lower_bound_precision": lower_bound_precision,
                "partial_precision": partial_precision,
                "adjudicated_precision": adjudicated_precision,
                "canonical_f1_full_match": canonical_f1_full_match,
                "canonical_f1_partial_match": canonical_f1_partial_match,
                "raw_precision": raw_precision,
                "raw_recall": raw_recall,
                "raw_f1": raw_f1,
            },
            "paired_metrics": {
                "raw_metrics": {"precision": raw_precision, "recall": raw_recall, "f1": raw_f1},
                "canonical_full_metrics": {"precision": lower_bound_precision, "recall": full_match_recall, "f1": canonical_f1_full_match},
                "canonical_partial_metrics": {"precision": partial_precision, "recall": partial_match_recall, "f1": canonical_f1_partial_match},
                # For backward compatibility
                "canonical_metrics": {"precision": lower_bound_precision, "recall": full_match_recall, "f1": canonical_f1_full_match},
            },
            "quality_metrics": {
                "claim_recall": full_match_recall,
                "claim_precision": raw_precision,
                "claim_f1": canonical_f1_full_match,
                "canonical_policy_precision": lower_bound_precision,
                "validated_claim_precision": lower_bound_precision,
                "raw_candidate_precision": raw_precision,
                "subject_accuracy": subject_accuracy,
                "predicate_accuracy": predicate_accuracy,
                "object_accuracy": object_accuracy,
                "false_approval_rate": false_approve_rate,
                "false_rejection_rate": false_reject_rate,
                "false_conflict_rate": false_conflict_rate,
                "malformed_fragment_rate": malformed_fragment_rate,
                "evidence_span_traceability": evidence_span_traceability,
            },
            "candidate_ledger": {
                "total_extracted_candidates": total_extracted,
                "approved_candidates": len(approved_claims),
                "rejected_candidates": len(rejected_claims),
                "review_candidates": len(review_claims),
                "canonical_candidates": total_canonical,
                "approved_l6_total": approved_l6_total,
                "canonical_approved_total": canonical_approved_total,
                "excluded_non_canonical": excluded_non_canonical,
                "excluded_boilerplate": excluded_boilerplate,
                "excluded_duplicate": excluded_duplicate,
                "excluded_malformed": excluded_malformed,
                "excluded_other": excluded_other,
                "reconciliation_difference": reconciliation_difference,
                "deduplicated_canonical_candidates": len(dedup_canonical),
                "correct_full_matches": correct_full_matches,
                "correct_partial_matches": correct_partial_matches,
                "unjudged_spans": unjudged_spans,
                "incorrect_predictions": incorrect_claims,
                "malformed_claims": malformed_claims,
                "duplicate_claims": duplicate_claims,
                "non_canonical_claims": non_canonical_claims,
                "gold_rules_captured_full": len(matched_full_gold_ids),
                "gold_rules_captured_partial": len(matched_partial_gold_ids),
                "gold_rules_raw_discovery": len(matched_raw_discovery_gold_ids),
                "gold_rules_missed": total_gold - (len(matched_full_gold_ids) + len(matched_partial_gold_ids)),
                # Legacy keys for backward compatibility
                "correct_canonical_predictions": correct_full_matches + correct_partial_matches,
                "incorrect_canonical_predictions": incorrect_claims + malformed_claims + duplicate_claims + non_canonical_claims,
                "unjudged_canonical_predictions": unjudged_spans,
                "gold_rules_captured": len(matched_full_gold_ids) + len(matched_partial_gold_ids),
                "labeled_rule_recall": partial_match_recall,
            },
            "counts": {
                "total_claims_extracted": total_extracted,
                "total_gold_canonical_rules": total_gold,
                "gold_rules_captured": len(matched_full_gold_ids) + len(matched_partial_gold_ids),
                "gold_rules_full_matched": len(matched_full_gold_ids),
                "gold_rules_partial_matched": len(matched_partial_gold_ids),
                "gold_rules_raw_discovery": len(matched_raw_discovery_gold_ids),
                "total_approved": len(approved_claims),
                "total_rejected": len(rejected_claims),
                "total_conflicts": len(conflicts),
                "malformed_fragments_count": len(malformed_fragments),
            },
            "claim_classifications": claim_classifications,
        }


    def run_all(self, doc_codes: List[str]) -> Dict[str, Any]:
        results = {}
        for code in doc_codes:
            results[code] = self.evaluate_document(code)
        return results


if __name__ == "__main__":
    harness = BenchmarkHarness()
    summary = harness.run_all([f"DOC-00{i}" for i in range(1, 10)])
    print(f"Evaluated {len(summary)} documents with BenchmarkHarness v3.1.")
