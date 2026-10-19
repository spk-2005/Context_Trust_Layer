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

p = Path("docs/Northwind_Refund_Policy_Handbook.pdf")
raw = p.read_bytes()
parsed = UniversalFileParser.parse_file(str(p), raw, "Northwind Refund Policy Handbook")
res = asyncio.run(UnifiedExtractionPipeline.execute(filename=p.name, raw_bytes=raw, options=UnifiedPipelineOptions(document_type="policy", persist_to_db=False)))
gold_p = Path("research/efficiency_audit_20/gold_labels/EFF-001_gold.json")
rep = GoldEvaluator.evaluate_against_gold(gold_p, res.candidates, parsed)

print(f"EFF-001: Total candidates: {len(res.candidates)}, Gold: {rep.total_gold_claims}, TP: {rep.true_positives}, FP: {rep.false_positives}, FN: {rep.false_negatives}")

print("\n--- FALSE NEGATIVES (Unmatched Gold) ---")
for i, fn in enumerate(rep.unmatched_gold):
    print(f"{i+1:02d}. [{fn.get('modality')}] {fn.get('subject')} | {fn.get('predicate')} | {fn.get('evidence_quote', '')[:100]}")

print("\n--- FALSE POSITIVES (Unmatched Extractions) ---")
for i, fp in enumerate(rep.unmatched_extractions):
    print(f"{i+1:02d}. [{fp.get('modality')}] {fp.get('subject')} | {fp.get('predicate')} | {fp.get('evidence', '')[:100]}")
