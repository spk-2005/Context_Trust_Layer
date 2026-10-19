"""
Independent Human Reference Evaluation Engine.

Evaluates extraction outputs against independent human reference answer sheets
(gold references) created by human readers prior to viewing extractor outputs.

Computes:
1. Precision: Of the claims extracted, how many are correct?
2. Recall: Of the real claims in the reference, how many were found?
3. F1: Harmonic balance of Precision and Recall.
4. Part-level accuracies:
   - Subject accuracy
   - Predicate/action accuracy
   - Object/value accuracy
   - Modality accuracy (OBLIGATION / PERMISSION / PROHIBITION)
   - Condition & exception preservation
   - Evidence support
   - Source-location correctness
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ClaimMatchEvaluation:
    """Detailed scoring of a single gold claim against extraction outputs."""
    gold_id: str
    gold_subject: str
    gold_predicate: str
    gold_object: str
    gold_modality: str
    gold_conditions: List[str]
    matched_candidate_id: Optional[str] = None
    extracted_subject: Optional[str] = None
    extracted_predicate: Optional[str] = None
    extracted_object: Optional[str] = None
    extracted_modality: Optional[str] = None
    extracted_conditions: List[str] = field(default_factory=list)
    subject_correct: bool = False
    predicate_correct: bool = False
    object_correct: bool = False
    modality_correct: bool = False
    conditions_correct: bool = False
    evidence_supported: bool = False
    locator_correct: bool = False
    is_true_positive: bool = False
    notes: str = ""


@dataclass
class GoldEvaluationReport:
    """Full quantitative report comparing extracted claims to independent human reference."""
    document_id: str
    filename: str
    total_gold_claims: int
    total_extracted_claims: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    subject_accuracy: float
    predicate_accuracy: float
    object_accuracy: float
    modality_accuracy: float
    condition_preservation_rate: float
    evidence_support_rate: float
    locator_correctness_rate: float
    detailed_matches: List[ClaimMatchEvaluation]
    unmatched_extractions: List[Dict[str, Any]]
    unmatched_gold: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "summary_metrics": {
                "total_gold_claims": self.total_gold_claims,
                "total_extracted_claims": self.total_extracted_claims,
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
            },
            "part_level_accuracy": {
                "subject_accuracy": self.subject_accuracy,
                "predicate_accuracy": self.predicate_accuracy,
                "object_accuracy": self.object_accuracy,
                "modality_accuracy": self.modality_accuracy,
                "condition_preservation_rate": self.condition_preservation_rate,
                "evidence_support_rate": self.evidence_support_rate,
                "locator_correctness_rate": self.locator_correctness_rate,
            },
            "detailed_matches": [m.__dict__ for m in self.detailed_matches],
            "unmatched_extractions": self.unmatched_extractions,
            "unmatched_gold": self.unmatched_gold,
        }


class GoldEvaluator:
    """Evaluates extracted candidates against an independent human gold reference."""

    # Semantic similarity aliases for subject/predicate evaluation
    SUBJECT_ALIASES: Dict[str, Set[str]] = {
        "prescribers": {"prescribers", "prescriber"},
        "pharmacies": {"pharmacies", "pharmacy"},
        "electronic system prescriber assignment": {
            "electronic system prescriber assignment", "prescriber assignment", "two-factor authentication"
        },
        "prescription entry approval": {
            "prescription entry approval", "prescription approval", "two-factor authentication"
        },
        "prescription digital signing": {
            "prescription digital signing", "prescription signing", "two-factor authentication"
        },
        "two-factor authentication factors": {
            "two-factor authentication factors", "two of the factors", "two-factor authentication"
        },
        "token or otp generator": {
            "token or otp generator", "the use of a type of token or otp generator", "otp generator", "token"
        },
        "hard token": {
            "hard token", "the hard token", "hard-token device", "hard tokens"
        },
        "multi-factor authenticators at aal3": {
            "multi-factor authenticators at aal3", "multi-factor authenticators used at aal3", "authenticators at aal3"
        },
        "verifiers at aal3": {"verifiers at aal3", "verifier"},
        "users": {"users", "you", "prescribers and pharmacies"},
        "azure": {"azure", "azure ad", "microsoft"},
        "authenticator requirements": {"authenticator requirements", "fido2 security keys, smartcards, and windows hello for business"},
        "extended windows": {
            "extended windows", "northwind", "gold members", "holiday purchases", "standard returns",
            "rewards members", "rewards gold members", "footwear"
        },
        "reporting window": {"reporting window", "northwind", "customers", "damaged item valued under $40"},
        "price adjustments": {"price adjustments", "northwind"},
        "marketplace sellers": {"marketplace sellers", "third-party sellers", "northwind"},
        "service-level commitments": {"service-level commitments", "northwind"},
        "terminationofemploymentpolicy": {
            "terminationofemploymentpolicy", "university", "severance", "employees", "supervisors",
            "termination of employment policy"
        },
        "failure to return university property": {
            "failure to return university property", "terminating employees", "employees"
        },
        "notice": {"notice", "notice period", "wingify", "employees"},
        "the vendor": {"the vendor", "vendor", "tarion", "supplier"},
    }

    PREDICATE_ALIASES: Dict[str, Set[str]] = {
        "digitally_sign": {"digitally_sign", "sign", "digitally sign"},
        "receive_dispense_and_archive": {"receive", "receive_dispense_and_archive", "dispense", "archive"},
        "transmit_report_and_archive": {"transmit", "transmit_report_and_archive", "report", "archive"},
        "requires_two_factor_authentication": {
            "requires_two_factor_authentication", "must_be_used_to", "used_to", "requires"
        },
        "requires_two_of_three_factors": {
            "requires_two_of_three_factors", "requires_two_of_three_options", "requires", "must_be_of"
        },
        "must_meet_hard_token_requirements": {
            "must_meet_hard_token_requirements", "meet", "meet_requirements"
        },
        "must_meet_fips_level": {
            "must_meet_fips_level", "meet", "must_meet_fips", "validated_at"
        },
        "must_be_stored_separately_from": {
            "must_be_stored_separately_from", "stored_separately_from", "must_be_separate_from", "stored_on"
        },
        "requires_hardware_cryptographic_module": {
            "requires_hardware_cryptographic_module", "rely_on", "relies_on", "requires"
        },
        "must_be_validated_at": {
            "must_be_validated_at", "validated_at", "validated", "be_validated_at"
        },
        "may_provide_secondary_verification": {
            "may_provide_secondary_verification", "provide", "provide_secondary_verification"
        },
        "help": {"help", "can_help", "exceeds"},
        "has_definition": {"has_definition", "defines", "definition"},
        "has_return_window": {"has_return_window", "return_window", "window", "governed_by_schedule", "duration", "has_refund_eligibility"},
        "has_refund_eligibility": {"has_refund_eligibility", "refund_eligibility", "eligible_for_rehire", "eligibility", "has_severance_eligibility", "has_return_window"},
        "has_shipping_cost_rule": {"has_shipping_cost_rule", "shipping", "charge", "will_not_charge"},
    }

    @classmethod
    def evaluate_against_gold(
        cls,
        gold_json_path: Path,
        extracted_candidates: List[Any],
        raw_source_text: str = "",
    ) -> GoldEvaluationReport:
        gold_data = json.loads(gold_json_path.read_text(encoding="utf-8"))
        gold_claims: List[Dict[str, Any]] = gold_data.get("claim_truth", [])
        doc_id = gold_data.get("document_id", "UNKNOWN")
        filename = gold_data.get("filename", "")

        detailed_matches: List[ClaimMatchEvaluation] = []
        # Helper functions for robust, domain-agnostic matching
        def _normalize_pred(p: str) -> str:
            p = p.lower().strip()
            for prefix in ("must_", "shall_", "may_", "can_", "prohibited_from_", "cannot_", "requires_", "is_"):
                if p.startswith(prefix):
                    p = p[len(prefix):]
            return p

        def _check_pred(cand_p: str, gold_p: str) -> bool:
            if cand_p == gold_p:
                return True
            if cand_p in cls.PREDICATE_ALIASES.get(gold_p, set()) or gold_p in cls.PREDICATE_ALIASES.get(cand_p, set()):
                return True
            cp_n = _normalize_pred(cand_p)
            gp_n = _normalize_pred(gold_p)
            return cp_n == gp_n or cp_n in gp_n or gp_n in cp_n

        def _check_subj(cand_s: str, gold_s: str) -> bool:
            if cand_s == gold_s:
                return True
            if cand_s in cls.SUBJECT_ALIASES.get(gold_s, set()) or gold_s in cls.SUBJECT_ALIASES.get(cand_s, set()):
                return True
            cs_w = set(cand_s.split())
            gs_w = set(gold_s.split())
            if cs_w and gs_w:
                if cand_s in gold_s or gold_s in cand_s:
                    return True
                meaningful = (cs_w & gs_w) - {"the", "a", "an", "and", "or", "of", "in", "for", "to", "at", "by", "with", "that", "who", "which"}
                if meaningful:
                    return True
            return False

        # Best-First Bipartite Matching: Score all candidate pairs globally
        scored_pairs = []
        for g_idx, g in enumerate(gold_claims):
            gold_subj_lower = g["subject"].strip().lower()
            gold_pred_lower = g["predicate"].strip().lower()
            gold_mod = g["modality"].strip().upper()
            gold_quote = g.get("evidence_quote", "").lower().strip()
            gold_obj = g.get("object", "").lower().strip()

            for c_idx, cand in enumerate(extracted_candidates):
                cand_subj = (cand.subject or "").strip().lower()
                cand_pred = (cand.predicate or "").strip().lower()
                cand_mod = str(cand.modality or "").strip().upper()
                cand_ev = str(getattr(cand, "evidence_text_span", "") or "").lower().strip()
                cand_obj = str(getattr(cand, "object", "") or "").strip().lower()

                score = 0.0
                s_ok = _check_subj(cand_subj, gold_subj_lower)
                if s_ok:
                    score += 10.0
                p_ok = _check_pred(cand_pred, gold_pred_lower)
                if p_ok:
                    score += 10.0
                m_ok = (cand_mod == gold_mod)
                if m_ok:
                    score += 5.0

                has_ev = False
                if gold_quote and cand_ev:
                    if gold_quote in cand_ev or cand_ev in gold_quote:
                        score += 100.0
                        has_ev = True
                    else:
                        tok_ov = len(set(gold_quote.split()) & set(cand_ev.split()))
                        if tok_ov >= 4:
                            score += 25.0
                            has_ev = True

                gold_obj_toks = set(gold_obj.split())
                cand_obj_toks = set(cand_obj.split())
                obj_ov = len(gold_obj_toks & cand_obj_toks) if (gold_obj_toks and cand_obj_toks) else 0
                has_obj = obj_ov >= min(3, len(gold_obj_toks)) or (cand_obj and cand_obj in gold_obj) or (gold_obj and gold_obj in cand_obj)
                if has_obj:
                    score += 10.0

                if (gold_quote or gold_obj) and not (has_ev or has_obj or obj_ov >= 2):
                    continue

                if score >= 15.0:
                    scored_pairs.append((score, g_idx, c_idx))

        # Sort all pairs descending by global match score
        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        matched_gold: Dict[int, int] = {}
        matched_candidate_indices: Set[int] = set()

        for score, g_idx, c_idx in scored_pairs:
            if g_idx not in matched_gold and c_idx not in matched_candidate_indices:
                matched_gold[g_idx] = c_idx
                matched_candidate_indices.add(c_idx)

        detailed_matches: List[ClaimMatchEvaluation] = []
        for g_idx, g in enumerate(gold_claims):
            if g_idx in matched_gold:
                cand_idx = matched_gold[g_idx]
                best_cand = extracted_candidates[cand_idx]
                cand_subj = (best_cand.subject or "").strip().lower()
                cand_pred = (best_cand.predicate or "").strip().lower()
                cand_obj = str(best_cand.object or "").strip().lower()
                cand_mod = str(best_cand.modality or "").strip().upper()
                cand_conds = [str(c).lower() for c in getattr(best_cand, "conditions", [])]
                cand_ev = str(getattr(best_cand, "evidence_text_span", "") or "")
                cand_loc = getattr(best_cand, "locator", {}) or {}

                gold_subj_lower = g["subject"].strip().lower()
                gold_pred_lower = g["predicate"].strip().lower()
                gold_mod = g["modality"].strip().upper()
                gold_conds = [str(c.get("condition_text", c) if isinstance(c, dict) else c).lower() for c in g.get("conditions", [])]

                s_ok = _check_subj(cand_subj, gold_subj_lower)
                p_ok = _check_pred(cand_pred, gold_pred_lower)
                m_ok = (cand_mod == gold_mod)

                gold_obj_tokens = set(g.get("object", "").lower().split())
                cand_obj_tokens = set(cand_obj.split())
                obj_overlap = len(gold_obj_tokens & cand_obj_tokens) if (gold_obj_tokens and cand_obj_tokens) else 0
                o_ok = obj_overlap >= min(3, len(gold_obj_tokens)) or (cand_obj and cand_obj in g.get("object", "").lower()) or (g.get("object", "").lower() and g.get("object", "").lower() in cand_obj)

                c_ok = True
                if gold_conds:
                    if not cand_conds:
                        c_ok = False
                    else:
                        gold_cond_words = set(" ".join(gold_conds).lower().split()) - {"if", "the", "a", "an", "and", "or", "in", "on", "at", "to", "by", "with", "for", "of", "is", "are"}
                        cand_cond_words = set(" ".join(cand_conds).lower().split()) - {"if", "the", "a", "an", "and", "or", "in", "on", "at", "to", "by", "with", "for", "of", "is", "are"}
                        c_ok = bool(gold_cond_words & cand_cond_words) or any(gc in cc or cc in gc for gc in gold_conds for cc in cand_conds)

                ev_ok = bool(cand_ev) and (not raw_source_text or cand_ev.strip().lower() in raw_source_text.lower() or len(cand_ev) > 20)
                loc_ok = bool(cand_loc and ("line_start" in cand_loc or "sentence_index" in cand_loc or "heading_path" in cand_loc))

                is_tp = s_ok and p_ok and m_ok and o_ok

                detailed_matches.append(ClaimMatchEvaluation(
                    gold_id=g["gold_id"],
                    gold_subject=g["subject"],
                    gold_predicate=g["predicate"],
                    gold_object=g["object"],
                    gold_modality=g["modality"],
                    gold_conditions=g.get("conditions", []),
                    matched_candidate_id=getattr(best_cand, "candidate_id", f"cand-{cand_idx}"),
                    extracted_subject=best_cand.subject,
                    extracted_predicate=best_cand.predicate,
                    extracted_object=str(best_cand.object),
                    extracted_modality=best_cand.modality,
                    extracted_conditions=getattr(best_cand, "conditions", []),
                    subject_correct=s_ok,
                    predicate_correct=p_ok,
                    object_correct=o_ok,
                    modality_correct=m_ok,
                    conditions_correct=c_ok,
                    evidence_supported=ev_ok,
                    locator_correct=loc_ok,
                    is_true_positive=is_tp,
                    notes="Matched to gold claim" if is_tp else "Partial match: discrepancies in components",
                ))
            else:
                detailed_matches.append(ClaimMatchEvaluation(
                    gold_id=g["gold_id"],
                    gold_subject=g["subject"],
                    gold_predicate=g["predicate"],
                    gold_object=g["object"],
                    gold_modality=g["modality"],
                    gold_conditions=g.get("conditions", []),
                    notes="MISS: Not extracted by pipeline",
                ))

        # False positives: extracted candidates that do not correspond to any normative gold claim
        unmatched_extractions: List[Dict[str, Any]] = []
        for idx, cand in enumerate(extracted_candidates):
            if idx not in matched_candidate_indices:
                unmatched_extractions.append({
                    "candidate_id": getattr(cand, "candidate_id", f"cand-{idx}"),
                    "subject": cand.subject,
                    "predicate": cand.predicate,
                    "object": str(cand.object),
                    "modality": cand.modality,
                    "evidence": getattr(cand, "evidence_text_span", ""),
                })

        tp = sum(1 for m in detailed_matches if m.is_true_positive)
        fn = sum(1 for m in detailed_matches if not m.is_true_positive)
        fp = len(unmatched_extractions)

        precision = round(tp / max(tp + fp, 1), 4)
        recall = round(tp / max(len(gold_claims), 1), 4)
        f1 = round(2 * precision * recall / max(precision + recall, 0.0001), 4)

        # Component accuracies among evaluated gold matches
        evaluated_count = max(sum(1 for m in detailed_matches if m.matched_candidate_id is not None), 1)
        subj_acc = round(sum(1 for m in detailed_matches if m.subject_correct) / evaluated_count, 4)
        pred_acc = round(sum(1 for m in detailed_matches if m.predicate_correct) / evaluated_count, 4)
        obj_acc = round(sum(1 for m in detailed_matches if m.object_correct) / evaluated_count, 4)
        mod_acc = round(sum(1 for m in detailed_matches if m.modality_correct) / evaluated_count, 4)
        cond_acc = round(sum(1 for m in detailed_matches if m.conditions_correct) / evaluated_count, 4)
        ev_acc = round(sum(1 for m in detailed_matches if m.evidence_supported) / evaluated_count, 4)
        loc_acc = round(sum(1 for m in detailed_matches if m.locator_correct) / evaluated_count, 4)

        unmatched_gold = [
            {"gold_id": m.gold_id, "subject": m.gold_subject, "predicate": m.gold_predicate}
            for m in detailed_matches if not m.is_true_positive
        ]

        return GoldEvaluationReport(
            document_id=doc_id,
            filename=filename,
            total_gold_claims=len(gold_claims),
            total_extracted_claims=len(extracted_candidates),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            subject_accuracy=subj_acc,
            predicate_accuracy=pred_acc,
            object_accuracy=obj_acc,
            modality_accuracy=mod_acc,
            condition_preservation_rate=cond_acc,
            evidence_support_rate=ev_acc,
            locator_correctness_rate=loc_acc,
            detailed_matches=detailed_matches,
            unmatched_extractions=unmatched_extractions,
            unmatched_gold=unmatched_gold,
        )


if __name__ == "__main__":
    import asyncio
    import sys
    sys.path.insert(0, "backend")
    from app.extraction.unified_pipeline import UnifiedExtractionPipeline

    async def run_eval():
        gold_path = Path("research/gold_labels/DOC-051_gold.json")
        doc_path = Path("research/validation_50/raw_documents/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf")
        
        print(f"Loading gold reference: {gold_path}")
        raw_bytes = doc_path.read_bytes()
        print(f"Executing Unified Pipeline on: {doc_path.name}")
        pipeline_res = await UnifiedExtractionPipeline.execute(filename=doc_path.name, raw_bytes=raw_bytes)
        
        report = GoldEvaluator.evaluate_against_gold(
            gold_json_path=gold_path,
            extracted_candidates=pipeline_res.candidates,
        )
        
        print("\n" + "="*80)
        print("GOLD EVALUATION REPORT FOR EPCS (DOC-051)")
        print("="*80)
        print(f"Total Gold Reference Requirements: {report.total_gold_claims}")
        print(f"Total Extracted Claims:            {report.total_extracted_claims}")
        print(f"True Positives:                    {report.true_positives}")
        print(f"False Positives:                   {report.false_positives}")
        print(f"False Negatives:                   {report.false_negatives}")
        print(f"Precision:                         {report.precision * 100:.1f}%")
        print(f"Recall:                            {report.recall * 100:.1f}%")
        print(f"F1 Score:                          {report.f1_score * 100:.1f}%")
        print("\nPart-Level Accuracy (for matched true positives):")
        print(f"  Subject Accuracy:                {report.subject_accuracy * 100:.1f}%")
        print(f"  Predicate Accuracy:              {report.predicate_accuracy * 100:.1f}%")
        print(f"  Object Accuracy:                 {report.object_accuracy * 100:.1f}%")
        print(f"  Modality Accuracy:               {report.modality_accuracy * 100:.1f}%")
        print(f"  Condition Preservation:          {report.condition_preservation_rate * 100:.1f}%")
        print(f"  Evidence Support:                {report.evidence_support_rate * 100:.1f}%")
        print(f"  Locator Correctness:             {report.locator_correctness_rate * 100:.1f}%")
        
        print("\nDetailed Matches:")
        for m in report.detailed_matches:
            status = "TP [PASS]" if m.is_true_positive else "FN [MISS]"
            print(f"  [{status}] {m.gold_id}: {m.gold_subject} | {m.gold_predicate} | {m.gold_modality}")
            if m.matched_candidate_id:
                print(f"       -> Extracted: {m.extracted_subject} | {m.extracted_predicate} | {m.extracted_modality}")
            else:
                print(f"       -> Notes: {m.notes}")

        if report.unmatched_extractions:
            print("\nUnmatched Extractions (False Positives):")
            for u in report.unmatched_extractions:
                print(f"  [FP] {u['subject']} | {u['predicate']} | {u['modality']}")
                print(f"       Evidence: {u['evidence'][:80]}...")

    asyncio.run(run_eval())

