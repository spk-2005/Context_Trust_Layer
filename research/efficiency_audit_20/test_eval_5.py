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

manifest = json.load(open("research/efficiency_audit_20/document_manifest.json", encoding="utf-8"))["documents"]
target_ids = {"EFF-004", "EFF-011", "EFF-014", "EFF-016", "EFF-017"}

async def eval_targets():
    for d in manifest:
        if d["document_id"] not in target_ids:
            continue
        p = Path(d["file_path"])
        raw = p.read_bytes()
        parsed = UniversalFileParser.parse_file(str(p), raw, d["title"])
        res = await UnifiedExtractionPipeline.execute(
            filename=p.name,
            raw_bytes=raw,
            options=UnifiedPipelineOptions(document_type=d["document_type"], persist_to_db=False)
        )
        gold_p = Path(f"research/efficiency_audit_20/gold_labels/{d['document_id']}_gold.json")
        rep = GoldEvaluator.evaluate_against_gold(gold_p, res.candidates, parsed)
        print(f"{d['document_id']} ({d['title'][:25]}): Gold={rep.total_gold_claims}, Cand={rep.total_extracted_claims}, TP={rep.true_positives}, FP={rep.false_positives}, FN={rep.false_negatives} | Precision={rep.precision*100:.1f}%, Recall={rep.recall*100:.1f}%, F1={rep.f1_score*100:.1f}%")

asyncio.run(eval_targets())
