import json
from pathlib import Path

docs = ['DOC-052', 'DOC-056', 'DOC-057', 'DOC-058', 'DOC-060']
tps = []
fps = []
fns = []

for d in docs:
    p = Path(f'research/validation_50/claim_audit/{d}_claims.json')
    if not p.exists():
        continue
    data = json.loads(p.read_text(encoding='utf-8'))
    for c in data.get('claims', []):
        if c.get('is_true_positive'):
            tps.append((d, c))
        elif not c.get('is_true_positive'):
            fns.append((d, c))
    for u in data.get('unmatched_extractions', []):
        fps.append((d, u))

print(f"=== TOTAL TRUE POSITIVES: {len(tps)} ===")
for d, c in tps:
    gid = c.get('gold_id')
    gs = c.get('gold_subject')
    gp = c.get('gold_predicate')
    gm = c.get('gold_modality')
    es = c.get('extracted_subject')
    ep = c.get('extracted_predicate')
    em = c.get('extracted_modality')
    go = str(c.get('gold_object'))[:70]
    eo = str(c.get('extracted_object'))[:70]
    print(f"[{d}] {gid}: Gold({gs} | {gp} | {gm}) <==> Extracted({es} | {ep} | {em})")
    print(f"     Gold Obj: {go}...")
    print(f"     Extr Obj: {eo}...\n")

print(f"=== TOTAL MISSED REFERENCE RULES (FNs): {len(fns)} ===")
for d, c in fns:
    gid = c.get('gold_id')
    gs = c.get('gold_subject')
    gp = c.get('gold_predicate')
    gm = c.get('gold_modality')
    go = str(c.get('gold_object'))[:70]
    note = c.get('notes')
    print(f"[{d}] {gid}: {gs} | {gp} | {gm}")
    print(f"     Obj: {go}...")
    print(f"     Note: {note}\n")

print(f"=== SAMPLE UNMATCHED EXTRACTIONS (FPs) ({len(fps)} total) ===")
for d, u in fps[:20]:
    s = u.get('subject')
    p = u.get('predicate')
    m = u.get('modality')
    o = str(u.get('object'))[:70]
    ev = str(u.get('evidence'))[:70]
    print(f"[{d}] {s} | {p} | {m}")
    print(f"     Obj: {o}...")
    print(f"     Ev:  {ev}...\n")
