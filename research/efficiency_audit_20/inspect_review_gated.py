import json
from pathlib import Path

docs = ['EFF-001', 'EFF-002', 'EFF-003', 'EFF-005', 'EFF-019', 'EFF-020']
for doc_id in docs:
    p = Path(f'research/efficiency_audit_20/extraction_results/{doc_id}_result.json')
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        q = data.get('quality', {})
        print(f"{doc_id}: Gold={q.get('gold_claims')}, Cand={len(data.get('candidates', []))}, TP={q.get('true_positives')}, FP={q.get('false_positives')}, FN={q.get('false_negatives')}, P={q.get('precision', 0)*100:.1f}%, R={q.get('recall', 0)*100:.1f}%")
