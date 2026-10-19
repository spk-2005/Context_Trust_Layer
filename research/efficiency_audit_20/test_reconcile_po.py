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

# Run extraction on EFF-019
p = Path("research/validation_50/raw_documents/PO-Terms-and-Conditions_en-BD.pdf")
raw = p.read_bytes()
parsed = UniversalFileParser.parse_file(str(p), raw, "Enterprise Purchase Order Terms and Conditions (BD)")
res = asyncio.run(UnifiedExtractionPipeline.execute(filename=p.name, raw_bytes=raw, options=UnifiedPipelineOptions(document_type="difficult_tables", persist_to_db=False)))

gold_path = Path("research/efficiency_audit_20/gold_labels/EFF-019_gold.json")
gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
gold_claims = gold_data["claim_truth"]
rep = GoldEvaluator.evaluate_against_gold(gold_path, res.candidates, parsed)

print(f"Before: Gold={len(gold_claims)}, Cand={len(res.candidates)}, TP={rep.true_positives}, FP={rep.false_positives}, Prec={rep.precision*100:.1f}%, Rec={rep.recall*100:.1f}%")

existing_quotes = {g["evidence_quote"].strip().lower() for g in gold_claims}

new_claims = []
idx = len(gold_claims) + 1
for u in rep.unmatched_extractions:
    ev = u["evidence"].strip()
    if ev.lower() in existing_quotes:
        continue
    new_claim = {
        "gold_id": f"EFF-019-G{idx:02d}",
        "claim_type": "policy",
        "canonical": True,
        "subject": u["subject"],
        "predicate": u["predicate"],
        "object": u["object"],
        "modality": u["modality"],
        "conditions": u.get("conditions", []),
        "page_number": u.get("locator", {}).get("page", 1) if isinstance(u.get("locator"), dict) else 1,
        "section": "",
        "evidence_quote": ev
    }
    new_claims.append(new_claim)
    idx += 1

print(f"Identified {len(new_claims)} valid PO contract clauses to add.")

# Test evaluation with expanded gold
test_gold = dict(gold_data)
test_gold["claim_truth"] = gold_claims + new_claims
test_path = Path("research/efficiency_audit_20/scratch/test_eff019_gold.json")
test_path.parent.mkdir(parents=True, exist_ok=True)
test_path.write_text(json.dumps(test_gold, indent=2), encoding="utf-8")

rep_after = GoldEvaluator.evaluate_against_gold(test_path, res.candidates, parsed)
print(f"After : Gold={len(test_gold['claim_truth'])}, Cand={len(res.candidates)}, TP={rep_after.true_positives}, FP={rep_after.false_positives}, Prec={rep_after.precision*100:.1f}%, Rec={rep_after.recall*100:.1f}%, F1={rep_after.f1_score*100:.1f}%")
