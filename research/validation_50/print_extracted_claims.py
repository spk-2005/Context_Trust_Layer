import json
from pathlib import Path

docs = ['DOC-052', 'DOC-056', 'DOC-057', 'DOC-058', 'DOC-060']
for d in docs:
    p = Path(f'research/validation_50/claim_audit/{d}_claims.json')
    if not p.exists():
        continue
    data = json.loads(p.read_text(encoding='utf-8'))
    print(f"==================================================")
    print(f"=== {d}: EXTRACTED CLAIMS ({len(data.get('claims', []))} gold, {data['claim_counts']['candidate_claims']} extracted) ===")
    print(f"==================================================")
    for c in data.get('claims', []):
        if c.get('is_true_positive'):
            print(f"[MATCHED TP] {c['gold_id']}: {c['extracted_subject']} | {c['extracted_predicate']} | {c['extracted_modality']}")
            print(f"   Obj: {c['extracted_object'][:80]}...")
    for u in data.get('unmatched_extractions', []):
        print(f"[UNMATCHED FP] {u.get('subject')} | {u.get('predicate')} | {u.get('modality')}")
        print(f"   Obj: {str(u.get('object'))[:80]}...")
        print(f"   Ev:  {str(u.get('evidence'))[:80]}...")
    print()
