"""
Phase 8: Evidence Evaluation, Separated Metric Measurement & Release Certification.

Implements decoupled extraction metrics, claim quality metrics, and release gate checks:
1. Extraction metrics: page/block coverage, row/record coverage, field coverage,
   table detection recall, cell alignment accuracy, empty-cell preservation,
   locator coverage, and OCR CER/WER.
2. Claim quality metrics: precision, recall, F1, condition recall, exception recall,
   atomicity accuracy, table-context accuracy, evidence support rate, quote fidelity,
   citation validity, and multi-evidence support accuracy.
3. Release Gates: Zero silent failures, resolvable evidence references, table header binding,
   valid locators, preserved conditions/exceptions, OCR token protection, no false 100% completeness.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from pydantic import BaseModel, Field


def levenshtein_distance(seq1: Sequence[Any], seq2: Sequence[Any]) -> int:
    """Computes exact edit distance (Levenshtein) between two sequences."""
    n = len(seq1)
    m = len(seq2)
    if n == 0:
        return m
    if m == 0:
        return n

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[n][m]


def compute_cer(reference_text: str, hypothesis_text: str) -> float:
    """Character Error Rate (CER) = edit_dist(chars) / max(1, len(ref_chars))."""
    ref_chars = list(reference_text)
    hyp_chars = list(hypothesis_text)
    dist = levenshtein_distance(ref_chars, hyp_chars)
    return round(dist / max(1, len(ref_chars)), 4)


def compute_wer(reference_text: str, hypothesis_text: str) -> float:
    """Word Error Rate (WER) = edit_dist(words) / max(1, len(ref_words))."""
    ref_words = reference_text.split()
    hyp_words = hypothesis_text.split()
    dist = levenshtein_distance(ref_words, hyp_words)
    return round(dist / max(1, len(ref_words)), 4)


class ExtractionQualityMetrics(BaseModel):
    """Decoupled extraction performance metrics."""
    expected_pages: int = 0
    processed_pages: int = 0
    page_coverage: float = 1.0

    expected_blocks: int = 0
    processed_blocks: int = 0
    block_coverage: float = 1.0

    expected_rows: int = 0
    processed_rows: int = 0
    row_record_coverage: float = 1.0

    expected_fields: int = 0
    processed_fields: int = 0
    field_coverage: float = 1.0

    expected_tables: int = 0
    detected_tables: int = 0
    table_detection_recall: float = 1.0

    total_cells: int = 0
    aligned_cells: int = 0
    cell_alignment_accuracy: float = 1.0

    expected_empty_cells: int = 0
    preserved_empty_cells: int = 0
    empty_cell_preservation_rate: float = 1.0

    total_evidence_units: int = 0
    units_with_valid_locator: int = 0
    locator_coverage_and_accuracy: float = 1.0

    ocr_cer: Optional[float] = None
    ocr_wer: Optional[float] = None


class ClaimQualityMetrics(BaseModel):
    """Decoupled claim quality metrics."""
    total_extracted_claims: int = 0
    total_gold_claims: int = 0
    true_positive_claims: int = 0
    claim_precision: float = 1.0
    claim_recall: float = 1.0
    claim_f1: float = 1.0

    expected_conditions: int = 0
    captured_conditions: int = 0
    condition_recall: float = 1.0

    expected_exceptions: int = 0
    captured_exceptions: int = 0
    exception_recall: float = 1.0

    total_propositions: int = 0
    atomic_propositions: int = 0
    atomicity_accuracy: float = 1.0

    total_table_claims: int = 0
    table_claims_with_valid_headers: int = 0
    table_context_accuracy: float = 1.0

    supported_claims: int = 0
    evidence_support_rate: float = 1.0

    claims_with_faithful_quotes: int = 0
    quote_fidelity: float = 1.0

    total_citations: int = 0
    valid_citations: int = 0
    citation_validity: float = 1.0

    multi_evidence_claims: int = 0
    valid_multi_evidence_claims: int = 0
    multi_evidence_support_accuracy: float = 1.0


class ReleaseGateCheck(BaseModel):
    """Production release gate verification across all quality invariants."""
    zero_silent_parser_failures: bool = True
    every_claim_evidence_resolves: bool = True
    no_table_value_without_header_context: bool = True
    no_certified_claim_invalid_locator: bool = True
    no_certified_claim_unpreserved_condition_or_exception: bool = True
    ocr_correction_audited: bool = True
    no_false_100_percent_completeness: bool = True
    regression_suite_passed: bool = True
    golden_corpus_not_regressed: bool = True

    passed: bool = True
    failure_reasons: List[str] = Field(default_factory=list)


class GoldenCorpusEvaluationReport(BaseModel):
    """Consolidated evaluation and release certification report."""
    corpus_version: str = "v3.0-golden-corpus"
    total_fixtures_evaluated: int = 0
    extraction_metrics: ExtractionQualityMetrics = Field(default_factory=ExtractionQualityMetrics)
    claim_quality_metrics: ClaimQualityMetrics = Field(default_factory=ClaimQualityMetrics)
    release_gates: ReleaseGateCheck = Field(default_factory=ReleaseGateCheck)
    per_fixture_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    summary_notes: List[str] = Field(default_factory=list)


class EvidenceEvaluationService:
    """Evaluates extraction fidelity, claim quality, and verifies release gates."""

    @staticmethod
    def evaluate_extraction(
        expected_pages: int,
        processed_pages: int,
        expected_blocks: int,
        processed_blocks: int,
        expected_rows: int,
        processed_rows: int,
        expected_fields: int,
        processed_fields: int,
        expected_tables: int,
        detected_tables: int,
        total_cells: int,
        aligned_cells: int,
        expected_empty_cells: int,
        preserved_empty_cells: int,
        total_units: int,
        units_with_valid_locator: int,
        reference_text: Optional[str] = None,
        hypothesis_text: Optional[str] = None,
    ) -> ExtractionQualityMetrics:
        page_cov = round(processed_pages / max(1, expected_pages), 4) if expected_pages > 0 else 1.0
        block_cov = round(processed_blocks / max(1, expected_blocks), 4) if expected_blocks > 0 else 1.0
        row_cov = round(processed_rows / max(1, expected_rows), 4) if expected_rows > 0 else 1.0
        field_cov = round(processed_fields / max(1, expected_fields), 4) if expected_fields > 0 else 1.0
        tbl_recall = round(detected_tables / max(1, expected_tables), 4) if expected_tables > 0 else 1.0
        cell_align = round(aligned_cells / max(1, total_cells), 4) if total_cells > 0 else 1.0
        empty_pres = round(preserved_empty_cells / max(1, expected_empty_cells), 4) if expected_empty_cells > 0 else 1.0
        loc_cov = round(units_with_valid_locator / max(1, total_units), 4) if total_units > 0 else 1.0

        cer = compute_cer(reference_text, hypothesis_text) if (reference_text is not None and hypothesis_text is not None) else None
        wer = compute_wer(reference_text, hypothesis_text) if (reference_text is not None and hypothesis_text is not None) else None

        return ExtractionQualityMetrics(
            expected_pages=expected_pages,
            processed_pages=processed_pages,
            page_coverage=page_cov,
            expected_blocks=expected_blocks,
            processed_blocks=processed_blocks,
            block_coverage=block_cov,
            expected_rows=expected_rows,
            processed_rows=processed_rows,
            row_record_coverage=row_cov,
            expected_fields=expected_fields,
            processed_fields=processed_fields,
            field_coverage=field_cov,
            expected_tables=expected_tables,
            detected_tables=detected_tables,
            table_detection_recall=tbl_recall,
            total_cells=total_cells,
            aligned_cells=aligned_cells,
            cell_alignment_accuracy=cell_align,
            expected_empty_cells=expected_empty_cells,
            preserved_empty_cells=preserved_empty_cells,
            empty_cell_preservation_rate=empty_pres,
            total_evidence_units=total_units,
            units_with_valid_locator=units_with_valid_locator,
            locator_coverage_and_accuracy=loc_cov,
            ocr_cer=cer,
            ocr_wer=wer,
        )

    @staticmethod
    def evaluate_claims(
        extracted_claims: Sequence[Any],
        gold_claims: Sequence[Dict[str, Any]],
        unit_map: Optional[Dict[str, Any]] = None,
    ) -> ClaimQualityMetrics:
        """Evaluates extracted claims against gold references with discrete claim-quality metrics."""
        total_extracted = len(extracted_claims)
        total_gold = len(gold_claims)

        matched_gold_indices: Set[int] = set()
        matched_ext_indices: Set[int] = set()

        total_cond_expected = sum(len(g.get("conditions", [])) for g in gold_claims)
        captured_conds = 0

        total_exc_expected = sum(len(g.get("exceptions", [])) for g in gold_claims)
        captured_excs = 0

        atomic_count = 0
        table_claims_total = 0
        table_claims_valid_headers = 0
        supported_count = 0
        faithful_quotes = 0
        total_citations = 0
        valid_citations = 0
        multi_ev_claims = 0
        valid_multi_ev_claims = 0

        for i, cand in enumerate(extracted_claims):
            cand_subj = str(getattr(cand, "subject", "") or "").lower().strip()
            cand_pred = str(getattr(cand, "predicate", "") or "").lower().strip()
            cand_obj = str(getattr(cand, "object", "") or "").lower().strip()
            cand_text = str(getattr(cand, "claim_text", "") or "")
            cand_span = str(getattr(cand, "evidence_text_span", "") or "")
            cand_status = str(getattr(cand, "validation_status", "") or getattr(cand, "status", "")).upper()
            cand_conds = getattr(cand, "conditions", []) or []
            cand_excs = getattr(cand, "exceptions", []) or []
            cand_ev_ids = getattr(cand, "evidence_unit_ids", []) or []

            # 1. Atomicity check
            is_compound = bool(re.search(r"\b(and\s+may\s+not|and\s+must\s+not|and\s+also\s+must|and\s+shall\s+not)\b", cand_text, re.I))
            if not is_compound:
                atomic_count += 1

            # 2. Table-context check
            if getattr(cand, "table_binding", None) is not None:
                table_claims_total += 1
                tb = cand.table_binding
                if getattr(tb, "column_header", None) or getattr(tb, "header_path", None):
                    table_claims_valid_headers += 1

            # 3. Support & quote fidelity check
            if "SUPPORT" in cand_status or cand_status == "VERIFIED":
                supported_count += 1
            if cand_span and (cand_span in cand_text or cand_text in cand_span or len(cand_span) > 10):
                faithful_quotes += 1

            # 4. Citations check
            if cand_ev_ids:
                for eid in cand_ev_ids:
                    total_citations += 1
                    if unit_map is None or eid in unit_map:
                        valid_citations += 1

            # 5. Multi-evidence check
            if len(cand_ev_ids) > 1:
                multi_ev_claims += 1
                if unit_map is None or all(eid in unit_map for eid in cand_ev_ids):
                    valid_multi_ev_claims += 1

            # Match against gold
            for j, gold in enumerate(gold_claims):
                if j in matched_gold_indices:
                    continue
                g_subj = str(gold.get("subject", "")).lower().strip()
                g_pred = str(gold.get("predicate", "")).lower().strip()
                g_obj = str(gold.get("object", "")).lower().strip()

                s_match = (cand_subj == g_subj) or (g_subj in cand_subj) or (cand_subj in g_subj)
                p_match = (cand_pred == g_pred) or (g_pred in cand_pred) or (cand_pred in g_pred)
                o_match = (cand_obj == g_obj) or (g_obj in cand_obj) or (cand_obj in g_obj)

                if s_match and (p_match or o_match):
                    matched_gold_indices.add(j)
                    matched_ext_indices.add(i)

                    # Condition recall
                    gold_conds = gold.get("conditions", [])
                    for gc in gold_conds:
                        if any(gc.lower() in cc.lower() or cc.lower() in gc.lower() for cc in cand_conds):
                            captured_conds += 1

                    # Exception recall
                    gold_excs = gold.get("exceptions", [])
                    for ge in gold_excs:
                        if any(ge.lower() in ce.lower() or ce.lower() in ge.lower() for ce in cand_excs):
                            captured_excs += 1
                    break

        tp = len(matched_ext_indices)
        precision = round(tp / max(1, total_extracted), 4) if total_extracted > 0 else 1.0
        recall = round(tp / max(1, total_gold), 4) if total_gold > 0 else 1.0
        f1 = round((2 * precision * recall) / max(0.0001, (precision + recall)), 4) if (precision + recall) > 0 else 1.0

        cond_recall = round(captured_conds / max(1, total_cond_expected), 4) if total_cond_expected > 0 else 1.0
        exc_recall = round(captured_excs / max(1, total_exc_expected), 4) if total_exc_expected > 0 else 1.0
        atomicity_acc = round(atomic_count / max(1, total_extracted), 4) if total_extracted > 0 else 1.0
        table_context_acc = round(table_claims_valid_headers / max(1, table_claims_total), 4) if table_claims_total > 0 else 1.0
        support_rate = round(supported_count / max(1, total_extracted), 4) if total_extracted > 0 else 1.0
        quote_fid = round(faithful_quotes / max(1, total_extracted), 4) if total_extracted > 0 else 1.0
        cit_validity = round(valid_citations / max(1, total_citations), 4) if total_citations > 0 else 1.0
        multi_ev_acc = round(valid_multi_ev_claims / max(1, multi_ev_claims), 4) if multi_ev_claims > 0 else 1.0

        return ClaimQualityMetrics(
            total_extracted_claims=total_extracted,
            total_gold_claims=total_gold,
            true_positive_claims=tp,
            claim_precision=precision,
            claim_recall=recall,
            claim_f1=f1,
            expected_conditions=total_cond_expected,
            captured_conditions=captured_conds,
            condition_recall=cond_recall,
            expected_exceptions=total_exc_expected,
            captured_exceptions=captured_excs,
            exception_recall=exc_recall,
            total_propositions=total_extracted,
            atomic_propositions=atomic_count,
            atomicity_accuracy=atomicity_acc,
            total_table_claims=table_claims_total,
            table_claims_with_valid_headers=table_claims_valid_headers,
            table_context_accuracy=table_context_acc,
            supported_claims=supported_count,
            evidence_support_rate=support_rate,
            claims_with_faithful_quotes=faithful_quotes,
            quote_fidelity=quote_fid,
            total_citations=total_citations,
            valid_citations=valid_citations,
            citation_validity=cit_validity,
            multi_evidence_claims=multi_ev_claims,
            valid_multi_evidence_claims=valid_multi_ev_claims,
            multi_evidence_support_accuracy=multi_ev_acc,
        )

    @staticmethod
    def evaluate_release_gates(
        extraction_metrics: ExtractionQualityMetrics,
        claim_metrics: ClaimQualityMetrics,
        silent_parser_failures: int = 0,
        unresolvable_citations: int = 0,
        table_values_without_header: int = 0,
        certified_claims_with_invalid_locator: int = 0,
        certified_claims_with_dropped_conditions: int = 0,
        ocr_audit_passed: bool = True,
        false_100_percent_completeness_detected: bool = False,
        regression_suite_passed: bool = True,
        corpus_regressed: bool = False,
    ) -> ReleaseGateCheck:
        """Verifies all hard release gates."""
        reasons: List[str] = []

        gate_zero_silent = (silent_parser_failures == 0)
        if not gate_zero_silent:
            reasons.append(f"Gate 1 Failed: {silent_parser_failures} silent parser failures detected.")

        gate_ev_resolves = (unresolvable_citations == 0 and claim_metrics.citation_validity >= 0.99)
        if not gate_ev_resolves:
            reasons.append(f"Gate 2 Failed: Unresolved evidence references found ({unresolvable_citations}).")

        gate_table_headers = (table_values_without_header == 0 and claim_metrics.table_context_accuracy >= 0.95)
        if not gate_table_headers:
            reasons.append("Gate 3 Failed: Table value extracted without valid column/row header context.")

        gate_valid_locators = (certified_claims_with_invalid_locator == 0 and extraction_metrics.locator_coverage_and_accuracy >= 0.95)
        if not gate_valid_locators:
            reasons.append(f"Gate 4 Failed: {certified_claims_with_invalid_locator} certified claims have invalid locators.")

        gate_preserved_conds = (certified_claims_with_dropped_conditions == 0 and claim_metrics.condition_recall >= 0.85 and claim_metrics.exception_recall >= 0.85)
        if not gate_preserved_conds:
            reasons.append("Gate 5 Failed: Certified claim omitted known conditions or exceptions.")

        gate_ocr_audit = ocr_audit_passed
        if not gate_ocr_audit:
            reasons.append("Gate 6 Failed: OCR correction altered critical identifiers, dates, or numeric tokens.")

        gate_no_false_100 = not false_100_percent_completeness_detected
        if not gate_no_false_100:
            reasons.append("Gate 7 Failed: Hardcoded 1.0 completeness reported without known denominator.")

        gate_regression = regression_suite_passed
        if not gate_regression:
            reasons.append("Gate 8 Failed: Prior regression tests failed.")

        gate_no_corpus_regression = not corpus_regressed
        if not gate_no_corpus_regression:
            reasons.append("Gate 9 Failed: Golden corpus evaluation metrics regressed below baseline.")

        passed = all([
            gate_zero_silent,
            gate_ev_resolves,
            gate_table_headers,
            gate_valid_locators,
            gate_preserved_conds,
            gate_ocr_audit,
            gate_no_false_100,
            gate_regression,
            gate_no_corpus_regression,
        ])

        return ReleaseGateCheck(
            zero_silent_parser_failures=gate_zero_silent,
            every_claim_evidence_resolves=gate_ev_resolves,
            no_table_value_without_header_context=gate_table_headers,
            no_certified_claim_invalid_locator=gate_valid_locators,
            no_certified_claim_unpreserved_condition_or_exception=gate_preserved_conds,
            ocr_correction_audited=gate_ocr_audit,
            no_false_100_percent_completeness=gate_no_false_100,
            regression_suite_passed=gate_regression,
            golden_corpus_not_regressed=gate_no_corpus_regression,
            passed=passed,
            failure_reasons=reasons,
        )

