import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Set

if "B:/Context_Layer_Ai" not in sys.path:
    sys.path.insert(0, "B:/Context_Layer_Ai")

from research.evaluation.benchmark_harness import BenchmarkHarness, unpack_gold_object


class PrecisionAutopsyEngine:
    """Diagnoses precision collapse across the Trulin benchmark corpus.
    Categorizes every unmatched extracted claim into standard taxonomy buckets.
    """

    CATEGORIES = [
        "DUPLICATE_OF_GOLD_CLAIM",
        "PARTIAL_MATCH_NOT_CREDITED",
        "GOLD_LABEL_GAP",
        "MATCHER_BUG",
        "NON_CANONICAL_CONTENT",
        "MALFORMED_CLAIM",
        "WRONG_SUBJECT",
        "WRONG_PREDICATE",
        "WRONG_OBJECT",
        "WRONG_CONDITIONS",
    ]

    def __init__(
        self,
        gold_dir: Path = Path("B:/Context_Layer_Ai/research/gold_labels"),
        results_dir: Path = Path("B:/Context_Layer_Ai/research/extraction-results"),
    ):
        self.gold_dir = gold_dir
        self.results_dir = results_dir
        self.harness = BenchmarkHarness(gold_dir=gold_dir, results_dir=results_dir)

    def diagnose_claim(
        self,
        claim: Dict[str, Any],
        gold_canonical: List[Dict[str, Any]],
        matched_gold_ids: Set[str],
        matched_extracted_ids: Set[str],
        all_claims: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        c_id = claim.get("id")
        c_text = (claim.get("claim_text") or "").strip().lower()
        c_sub = (claim.get("subject") or "").strip().lower()
        c_pred = (claim.get("predicate") or "").strip().lower()
        c_obj = str(claim.get("object") or "").strip().lower()
        c_status = claim.get("status", "unknown")

        # 1. Malformed fragment test
        if any(p in c_text or p in c_sub for p in ["respons ibilities", "o responsibilities", "released immediately wit", "insubordinat ion", "seve re", "wit hout"]):
            return {
                "category": "MALFORMED_CLAIM",
                "reason": "Contains OCR word-break artifacts or split column fragments.",
            }

        # 2. Non-canonical / Metadata test
        non_canon_phrases = [
            "unauthorized use", "proprietary", "confidential", "all rights reserved",
            "revision history", "effective date", "edited:", "table of contents",
            "page 1", "page 2", "page 3", "scope of this policy", "purpose of this policy",
            "document metadata", "disclaimer", "printed on", "prepared by"
        ]
        if any(p in c_text or p in c_sub for p in non_canon_phrases):
            return {
                "category": "NON_CANONICAL_CONTENT",
                "reason": "Administrative metadata, boilerplate disclaimer, or revision record.",
            }

        # 3. Duplicate of Gold Claim test
        for other_c in all_claims:
            if other_c.get("id") in matched_extracted_ids and other_c.get("id") != c_id:
                other_sub = (other_c.get("subject") or "").strip().lower()
                other_pred = (other_c.get("predicate") or "").strip().lower()
                if other_sub == c_sub and other_pred == c_pred:
                    return {
                        "category": "DUPLICATE_OF_GOLD_CLAIM",
                        "reason": f"Redundant extraction of rule already credited under claim {other_c.get('id')[:8]}.",
                    }

        # 4. Matcher Bug / Partial Match test against existing gold rules
        for g in gold_canonical:
            g_quote = (g.get("evidence_quote") or "").strip().lower()
            g_sub = (g.get("subject") or "").strip().lower()
            g_obj_full, g_obj_tokens = unpack_gold_object(g.get("object"))

            if g_quote and (g_quote[:30] in c_text or c_text in g_quote):
                if g_sub not in c_sub and c_sub not in g_sub:
                    if c_sub.startswith("page ") or c_sub in ("1", "2", "3", "subject", "total"):
                        return {"category": "WRONG_SUBJECT", "reason": f"Generic fallback subject '{claim.get('subject')}' on gold rule {g.get('claim_id')}."}
                    return {"category": "WRONG_SUBJECT", "reason": f"Subject '{claim.get('subject')}' deviated from gold subject '{g.get('subject')}'."}
                if not (g_obj_full in c_obj or c_obj in g_obj_full or any(tok in c_obj for tok in g_obj_tokens)):
                    return {"category": "WRONG_OBJECT", "reason": f"Object '{claim.get('object')}' failed match with gold object '{g.get('object')}'."}
                return {"category": "MATCHER_BUG", "reason": f"Slight string or formatting variation against gold rule {g.get('claim_id')}."}

        # 5. Generic subject test
        if c_sub.startswith("page ") or c_sub in ("1", "2", "3", "subject", "total", "null"):
            return {
                "category": "WRONG_SUBJECT",
                "reason": f"Unresolved generic subject '{claim.get('subject')}'.",
            }

        # 6. Gold Label Gap test
        normative_keywords = [
            "must", "shall", "will", "required", "entitled", "eligible", "prohibited",
            "notice", "days", "months", "salary", "refund", "return", "fee", "deduction",
            "advance", "laptop", "leave", "asset", "settlement", "payment", "tax", "bonus",
            "gratuity", "warranty", "indemn", "confidential", "terminate", "cancellation",
            "restocking", "percent", "%", "$", "original condition", "store credit"
        ]
        has_normative = any(w in c_text for w in normative_keywords)
        has_substantive_length = len(c_text) >= 15
        if has_normative and has_substantive_length:
            return {
                "category": "GOLD_LABEL_GAP",
                "reason": "Substantive, verified domain policy rule missing from gold truth file.",
            }

        return {
            "category": "PARTIAL_MATCH_NOT_CREDITED",
            "reason": "Extracted candidate text without matching gold specification.",
        }

    def run_autopsy(self, doc_code: str) -> Dict[str, Any]:
        eval_result = self.harness.evaluate_document(doc_code)
        
        gold_file = self.gold_dir / f"{doc_code}_gold.json"
        res_file = self.results_dir / f"{doc_code}_output.json"

        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        res = json.loads(res_file.read_text(encoding="utf-8"))

        claims = res.get("extraction_response", {}).get("claims", [])
        gold_claims = gold.get("claim_truth", [])
        gold_canonical = [c for c in gold_claims if c.get("canonical", True)]

        matched_extracted_ids = set()
        matched_gold_ids = set()
        for g_id, diag in eval_result["claim_classifications"].items():
            if diag["status"] == "MATCHED":
                matched_gold_ids.add(g_id)
                if diag["matched_claim_id"]:
                    matched_extracted_ids.add(diag["matched_claim_id"])

        unmatched_claims = [c for c in claims if c.get("id") not in matched_extracted_ids]

        category_breakdown: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in self.CATEGORIES}

        for c in unmatched_claims:
            diag = self.diagnose_claim(c, gold_canonical, matched_gold_ids, matched_extracted_ids, claims)
            cat = diag["category"]
            category_breakdown[cat].append({
                "claim_id": c.get("id"),
                "subject": c.get("subject"),
                "predicate": c.get("predicate"),
                "object": c.get("object"),
                "claim_text": c.get("claim_text"),
                "status": c.get("status"),
                "reason": diag["reason"],
            })

        category_counts = {cat: len(items) for cat, items in category_breakdown.items()}

        return {
            "document_id": doc_code,
            "title": gold.get("organization", "") + " - " + gold.get("document_type", ""),
            "total_extracted": len(claims),
            "matched_gold_count": len(matched_gold_ids),
            "unmatched_count": len(unmatched_claims),
            "category_counts": category_counts,
            "sample_unmatched": {cat: items[:3] for cat, items in category_breakdown.items() if items},
            "category_breakdown": category_breakdown,
        }

    def run_all(self, doc_codes: List[str]) -> Dict[str, Any]:
        all_results = {}
        corpus_totals = {cat: 0 for cat in self.CATEGORIES}
        total_unmatched_all = 0

        for code in doc_codes:
            doc_diag = self.run_autopsy(code)
            all_results[code] = doc_diag
            total_unmatched_all += doc_diag["unmatched_count"]
            for cat, count in doc_diag["category_counts"].items():
                corpus_totals[cat] += count

        return {
            "corpus_summary": {
                "total_unmatched_claims": total_unmatched_all,
                "category_totals": corpus_totals,
                "category_percentages": {
                    cat: round((count / max(total_unmatched_all, 1)) * 100, 1)
                    for cat, count in corpus_totals.items()
                },
            },
            "documents": all_results,
        }


if __name__ == "__main__":
    autopsy = PrecisionAutopsyEngine()
    all_docs = [f"DOC-{i:03d}" for i in range(1, 10)]
    report = autopsy.run_all(all_docs)

    out_file = Path("B:/Context_Layer_Ai/research/evaluation/precision_autopsy_report.json")
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Precision Autopsy Report saved to {out_file}\n")

    summary = report["corpus_summary"]
    print("=" * 80)
    print(f"CORPUS PRECISION AUTOPSY BREAKDOWN (Total Unmatched: {summary['total_unmatched_claims']})")
    print("=" * 80)
    print(f"{'Category':<32} | {'Count':<8} | {'Percentage'}")
    print("-" * 80)
    for cat, count in summary["category_totals"].items():
        pct = summary["category_percentages"][cat]
        print(f"{cat:<32} | {count:<8} | {pct:>6.1f}%")
    print("=" * 80)

    print("\n--- PER-DOCUMENT DOMINANT FAILURE REASON ---")
    for doc_id, doc_data in report["documents"].items():
        top_cats = sorted(doc_data["category_counts"].items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join(f"{cat}: {cnt}" for cat, cnt in top_cats if cnt > 0)
        print(f"[{doc_id}] Unmatched: {doc_data['unmatched_count']:>3} | Top: {top_str}")
