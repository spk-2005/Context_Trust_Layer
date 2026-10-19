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

p = Path("research/validation_50/raw_documents/PO-Terms-and-Conditions_en-BD.pdf")
raw = p.read_bytes()
parsed = UniversalFileParser.parse_file(str(p), raw, "Enterprise Purchase Order Terms and Conditions (BD)")
res = asyncio.run(UnifiedExtractionPipeline.execute(filename=p.name, raw_bytes=raw, options=UnifiedPipelineOptions(document_type="difficult_tables", persist_to_db=False)))
gold_p = Path("research/efficiency_audit_20/gold_labels/EFF-019_gold.json")
rep = GoldEvaluator.evaluate_against_gold(gold_p, res.candidates, parsed)

print(f"Total candidates: {len(res.candidates)}, Gold: {rep.total_gold_claims}, TP: {rep.true_positives}, FP: {rep.false_positives}")
print(f"Unmatched extractions count: {len(rep.unmatched_extractions)}")
for i, u in enumerate(rep.unmatched_extractions):
    print(f"{i+1:02d}. [{u['modality']}] {u['subject']} | {u['predicate']} | {u['evidence'][:120]}")
