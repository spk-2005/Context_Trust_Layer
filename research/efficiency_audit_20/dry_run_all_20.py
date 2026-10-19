import asyncio
import json
import os
import sys
import time
from pathlib import Path

os.environ["LLM_PROVIDER"] = "rule_engine"
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.universal_file_parser import UniversalFileParser
from app.validation_gate.models import ClaimLifecycleDecision
from research.evaluation.gold_evaluator import GoldEvaluator

manifest = json.load(open("research/efficiency_audit_20/document_manifest.json", encoding="utf-8"))["documents"]

total_tp = 0
total_fp = 0
total_fn = 0
total_gold = 0
total_cand = 0
total_app = 0
total_rev = 0
total_rej = 0

precisions = []
recalls = []
f1s = []

print(f"{'Doc ID':<8} | {'Title':<25} | {'Cand':<5} | {'App':<4} | {'Rev':<4} | {'Rej':<4} | {'Gold':<5} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Prec':<6} | {'Rec':<6} | {'F1':<6}")
print("-" * 105)

for d in manifest:
    p = Path(d["file_path"])
    raw = p.read_bytes()
    parsed = UniversalFileParser.parse_file(str(p), raw, d["title"])
    res = asyncio.run(UnifiedExtractionPipeline.execute(
        filename=p.name,
        raw_bytes=raw,
        options=UnifiedPipelineOptions(document_type=d["document_type"], persist_to_db=False)
    ))
    cands = res.candidates
    evals = res.evaluations
    
    app = sum(1 for e in evals if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE)
    rev = sum(1 for e in evals if e.lifecycle_decision == ClaimLifecycleDecision.REVIEW)
    rej = sum(1 for e in evals if e.lifecycle_decision == ClaimLifecycleDecision.REJECT)
    
    gold_p = Path(f"research/efficiency_audit_20/gold_labels/{d['document_id']}_gold.json")
    rep = GoldEvaluator.evaluate_against_gold(gold_p, cands, parsed)
    
    total_cand += len(cands)
    total_app += app
    total_rev += rev
    total_rej += rej
    total_gold += rep.total_gold_claims
    total_tp += rep.true_positives
    total_fp += rep.false_positives
    total_fn += rep.false_negatives
    
    precisions.append(rep.precision)
    recalls.append(rep.recall)
    f1s.append(rep.f1_score)
    
    print(f"{d['document_id']:<8} | {d['title'][:25]:<25} | {len(cands):<5} | {app:<4} | {rev:<4} | {rej:<4} | {rep.total_gold_claims:<5} | {rep.true_positives:<4} | {rep.false_positives:<4} | {rep.false_negatives:<4} | {rep.precision*100:5.1f}% | {rep.recall*100:5.1f}% | {rep.f1_score*100:5.1f}%")

macro_prec = sum(precisions) / len(precisions)
macro_rec = sum(recalls) / len(recalls)
macro_f1 = sum(f1s) / len(f1s)

micro_prec = total_tp / max(total_tp + total_fp, 1)
micro_rec = total_tp / max(total_tp + total_fn, 1)
micro_f1 = 2 * micro_prec * micro_rec / max(micro_prec + micro_rec, 1e-9)

print("-" * 105)
print(f"TOTALS   : Cand={total_cand} (App={total_app}, Rev={total_rev}, Rej={total_rej}) | Gold={total_gold} | TP={total_tp}, FP={total_fp}, FN={total_fn}")
print(f"MACRO    : Precision={macro_prec*100:.2f}%, Recall={macro_rec*100:.2f}%, F1={macro_f1*100:.2f}%")
print(f"MICRO    : Precision={micro_prec*100:.2f}%, Recall={micro_rec*100:.2f}%, F1={micro_f1*100:.2f}%")
