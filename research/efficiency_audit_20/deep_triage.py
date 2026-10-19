import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from research.evaluation.gold_evaluator import GoldEvaluator
import types

out_file = Path('research/efficiency_audit_20/deep_triage_utf8.txt').open('w', encoding='utf-8')
def p(*args):
    print(*args, file=out_file)
    print(*args)

docs = ['EFF-001', 'EFF-002', 'EFF-003', 'EFF-005', 'EFF-019', 'EFF-020']
for doc_id in docs:
    res_path = Path(f'research/efficiency_audit_20/extraction_results/{doc_id}_result.json')
    gold_path = Path(f'research/efficiency_audit_20/gold_labels/{doc_id}_gold.json')
    if not res_path.exists() or not gold_path.exists():
        continue
    
    res_data = json.loads(res_path.read_text(encoding='utf-8'))
    gold_data = json.loads(gold_path.read_text(encoding='utf-8'))
    
    src_path = Path(res_data['metadata']['file_path'])
    src_text = src_path.read_text(encoding='utf-8', errors='ignore')
    
    cands = [types.SimpleNamespace(
        candidate_id=c.get('candidate_id'),
        subject=c.get('subject'),
        predicate=c.get('predicate'),
        object=c.get('object'),
        modality=c.get('modality'),
        evidence_text_span=c.get('evidence'),
        locator=c.get('locator'),
        conditions=c.get('conditions', []),
    ) for c in res_data['candidates']]
    
    rep = GoldEvaluator.evaluate_against_gold(gold_path, cands, src_text)
    
    p("\n" + "="*80)
    p(f"TRIAGE FOR {doc_id} ({res_data['metadata']['title']}):")
    p(f"  Gold Rules: {rep.total_gold_claims} | Extracted: {rep.total_extracted_claims} | TP: {rep.true_positives} | FP: {rep.false_positives} | FN: {rep.false_negatives}")
    p(f"  Precision: {rep.precision*100:.1f}% | Recall: {rep.recall*100:.1f}% | F1: {rep.f1_score*100:.1f}%")
    p("="*80)
    
    p(f"\n>> UNMATCHED EXTRACTIONS (False Positives: {len(rep.unmatched_extractions)}):")
    for idx, u in enumerate(rep.unmatched_extractions, 1):
        p(f"  [{idx:02d}] {u['subject']} | {u['predicate']} | {u['modality']}")
        p(f"       Obj: {str(u['object'])[:80]}")
        p(f"       Ev:  {str(u['evidence'])[:100]}")
        
    if rep.unmatched_gold:
        p(f"\n>> UNMATCHED GOLD (False Negatives: {len(rep.unmatched_gold)}):")
        for idx, g in enumerate(rep.unmatched_gold, 1):
            p(f"  [{idx:02d}] {g['gold_id']}: {g['subject']} | {g['predicate']}")
out_file.close()
