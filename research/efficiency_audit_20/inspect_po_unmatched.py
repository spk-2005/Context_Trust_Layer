import json

data = json.load(open('research/efficiency_audit_20/extraction_results/EFF-019_result.json', encoding='utf-8'))
gold = json.load(open('research/efficiency_audit_20/gold_labels/EFF-019_gold.json', encoding='utf-8'))
gold_quotes = {g['evidence_quote'].strip().lower() for g in gold['claim_truth']}

unmatched = []
for c in data['candidates']:
    ev = c['evidence'].strip().lower()
    if not any(gq in ev or ev in gq for gq in gold_quotes):
        unmatched.append(c)

print(f"Total candidates in EFF-019: {len(data['candidates'])}")
print(f"Unmatched clauses count: {len(unmatched)}")
for idx, u in enumerate(unmatched, 1):
    print(f"{idx:02d}. [{u['modality']}] {u['subject']} | {u['predicate']} | {u['evidence'][:80]}")
