import json
from pathlib import Path

docs = ['DOC-052', 'DOC-056', 'DOC-057', 'DOC-058', 'DOC-060']
for d in docs:
    p = Path(f'research/validation_50/claim_audit/{d}_claims.json')
    if not p.exists():
        continue
    data = json.loads(p.read_text(encoding='utf-8'))
    for c in data.get('claims', []):
        if c.get('is_true_positive'):
            print(f"[{d}] {c['gold_id']}")
            print(f"  Gold:      {c['gold_subject']} | {c['gold_predicate']} | {c['gold_modality']}")
            print(f"  Gold Obj:  {c['gold_object']}")
            print(f"  Extracted: {c['extracted_subject']} | {c['extracted_predicate']} | {c['extracted_modality']}")
            print(f"  Extr Obj:  {c['extracted_object']}")
            print(f"  Conditions:{c.get('extracted_conditions')}")
            print()
