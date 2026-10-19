import json
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "backend")
sys.path.insert(0, ".")
from research.evaluation.gold_evaluator import GoldEvaluator

docs = ['EFF-001', 'EFF-002', 'EFF-003', 'EFF-005', 'EFF-019', 'EFF-020']
for doc_id in docs:
    p = Path(f'research/efficiency_audit_20/extraction_results/{doc_id}_result.json')
    if not p.exists():
        continue
    data = json.loads(p.read_text(encoding='utf-8'))
    gold_path = Path(f'research/efficiency_audit_20/gold_labels/{doc_id}_gold.json')
    gold_data = json.loads(gold_path.read_text(encoding='utf-8'))
    
    print("=" * 80)
    print(f"DOCUMENT: {doc_id} - {data['metadata']['title']}")
    print(f"Quality: TP={data['quality']['true_positives']}, FP={data['quality']['false_positives']}, FN={data['quality']['false_negatives']}, P={data['quality']['precision']*100:.1f}%, R={data['quality']['recall']*100:.1f}%")
    print("=" * 80)
    
    # Let's inspect gold report detailed matches
    import types
    cands = [types.SimpleNamespace(
        candidate_id=c.get('candidate_id'),
        subject=c.get('subject'),
        predicate=c.get('predicate'),
        object=c.get('object'),
        modality=c.get('modality'),
        evidence_text_span=c.get('evidence'),
        locator=c.get('locator'),
        conditions=c.get('conditions', []),
    ) for c in data['candidates']]
    
    # We can run evaluator to get unmatched
    # Or read parsed_doc
    src_path = Path(data['metadata']['file_path'])
    src_text = src_path.read_text(encoding='utf-8', errors='ignore')
    report = GoldEvaluator.evaluate_against_gold(gold_path, cands, src_text)
    
    print(f"\n--- UNMATCHED EXTRACTIONS (False Positives: {len(report.unmatched_extractions)}) ---")
    for idx, u in enumerate(report.unmatched_extractions[:10], 1):
        print(f"  {idx}. [{u.get('modality')}] Subj: {u.get('subject')} | Pred: {u.get('predicate')} | Obj: {str(u.get('object'))[:50]}")
        print(f"     Evidence: {str(u.get('evidence'))[:100]}")
        
    if report.unmatched_gold:
        print(f"\n--- UNMATCHED GOLD RULES (False Negatives: {len(report.unmatched_gold)}) ---")
        for idx, g in enumerate(report.unmatched_gold[:10], 1):
            print(f"  {idx}. Subj: {g.get('subject')} | Pred: {g.get('predicate')}")
