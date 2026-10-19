import sys
import json
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

results_dir = Path("research/efficiency_audit_20/extraction_results")
gold_dir = Path("research/efficiency_audit_20/gold_labels")
weak_docs = ["EFF-014", "EFF-004", "EFF-016", "EFF-017", "EFF-011"]

for doc_id in weak_docs:
    res = json.loads((results_dir / f"{doc_id}_result.json").read_text(encoding="utf-8"))
    gold = json.loads((gold_dir / f"{doc_id}_gold.json").read_text(encoding="utf-8"))
    print(f"\n=======================================================")
    print(f"{doc_id}: {res['metadata']['title']}")
    print(f"Candidates: {len(res['candidates'])}, Gold Rules: {len(gold['claim_truth'])}")
    print("-------------------------------------------------------")
    print("GOLD RULES:")
    for g in gold["claim_truth"]:
        print(f"  * {g['subject']} | {g['predicate']} | {g['modality']} | {str(g['object'])[:60]}")
    print("-------------------------------------------------------")
    print("EXTRACTED CANDIDATES:")
    for idx, c in enumerate(res["candidates"], 1):
        ev = (c.get("evidence") or "")[:50].replace('\n', ' ')
        print(f"  {idx}. {c.get('subject')} | {c.get('predicate')} | {c.get('modality')} | {str(c.get('object'))[:50]} (Ev: {ev})")

