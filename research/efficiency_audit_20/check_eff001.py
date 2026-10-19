import json

data = json.load(open('research/efficiency_audit_20/extraction_results/EFF-001_result.json', encoding='utf-8'))
for idx, c in enumerate(data['candidates'], 1):
    subj = c.get('subject', '')
    pred = c.get('predicate', '')
    obj = str(c.get('object', ''))[:50]
    ev = str(c.get('evidence', ''))[:50]
    mod = c.get('modality', '')
    print(f"{idx:02d}. [{mod}] {subj} | {pred} | {obj}")
