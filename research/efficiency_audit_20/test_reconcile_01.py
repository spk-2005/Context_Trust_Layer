import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["LLM_PROVIDER"] = "rule_engine"
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.universal_file_parser import UniversalFileParser
from research.evaluation.gold_evaluator import GoldEvaluator

# Run extraction on EFF-001
p = Path("docs/Northwind_Refund_Policy_Handbook.pdf")
raw = p.read_bytes()
parsed = UniversalFileParser.parse_file(str(p), raw, "Northwind Refund Policy Handbook")
res = asyncio.run(UnifiedExtractionPipeline.execute(filename=p.name, raw_bytes=raw, options=UnifiedPipelineOptions(document_type="policy", persist_to_db=False)))

gold_path = Path("research/efficiency_audit_20/gold_labels/EFF-001_gold.json")
gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
gold_claims = gold_data["claim_truth"]
rep = GoldEvaluator.evaluate_against_gold(gold_path, res.candidates, parsed)

print(f"EFF-001 Before: Gold={len(gold_claims)}, Cand={len(res.candidates)}, TP={rep.true_positives}, FP={rep.false_positives}, FN={rep.false_negatives}, Prec={rep.precision*100:.1f}%, Rec={rep.recall*100:.1f}%")

print("\n--- Unmatched Gold (FN) ---")
for fn in rep.unmatched_gold:
    print(f"ID={fn.get('gold_id')}, Subj={fn.get('subject')}, Pred={fn.get('predicate')}, Quote={repr(fn.get('evidence_quote', ''))[:80]}")

print("\n--- Unmatched Extractions (FP) ---")
for fp in rep.unmatched_extractions:
    print(f"Subj={fp.get('subject')}, Pred={fp.get('predicate')}, Quote={repr(fp.get('evidence', ''))[:80]}")
