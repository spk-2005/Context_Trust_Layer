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
from research.evaluation.gold_evaluator import GoldEvaluator, ClaimMatchEvaluation, GoldEvaluationReport

p = Path("docs/Northwind_Refund_Policy_Handbook.pdf")
raw = p.read_bytes()
parsed = UniversalFileParser.parse_file(str(p), raw, "Northwind Refund Policy Handbook")
res = asyncio.run(UnifiedExtractionPipeline.execute(filename=p.name, raw_bytes=raw, options=UnifiedPipelineOptions(document_type="policy", persist_to_db=False)))

gold_path = Path("research/efficiency_audit_20/gold_labels/EFF-001_gold.json")
gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
gold_claims = gold_data.get("claim_truth", [])

def _normalize_pred(p: str) -> str:
    p = p.lower().strip()
    for prefix in ("must_", "shall_", "may_", "can_", "prohibited_from_", "cannot_", "requires_", "is_"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return p

def _check_pred(cand_p: str, gold_p: str) -> bool:
    if cand_p == gold_p:
        return True
    if cand_p in GoldEvaluator.PREDICATE_ALIASES.get(gold_p, set()) or gold_p in GoldEvaluator.PREDICATE_ALIASES.get(cand_p, set()):
        return True
    cp_n = _normalize_pred(cand_p)
    gp_n = _normalize_pred(gold_p)
    return cp_n == gp_n or cp_n in gp_n or gp_n in cp_n

def _check_subj(cand_s: str, gold_s: str) -> bool:
    if cand_s == gold_s:
        return True
    if cand_s in GoldEvaluator.SUBJECT_ALIASES.get(gold_s, set()) or gold_s in GoldEvaluator.SUBJECT_ALIASES.get(cand_s, set()):
        return True
    cs_w = set(cand_s.split())
    gs_w = set(gold_s.split())
    if cs_w and gs_w:
        if cand_s in gold_s or gold_s in cand_s:
            return True
        meaningful = (cs_w & gs_w) - {"the", "a", "an", "and", "or", "of", "in", "for", "to", "at", "by", "with", "that", "who", "which"}
        if meaningful:
            return True
    return False

# Build scoring table
scored_pairs = []
for g_idx, g in enumerate(gold_claims):
    gold_subj_lower = g["subject"].strip().lower()
    gold_pred_lower = g["predicate"].strip().lower()
    gold_mod = g["modality"].strip().upper()
    gold_quote = g.get("evidence_quote", "").lower().strip()
    gold_obj = g.get("object", "").lower().strip()

    for c_idx, cand in enumerate(res.candidates):
        cand_subj = (cand.subject or "").strip().lower()
        cand_pred = (cand.predicate or "").strip().lower()
        cand_mod = str(cand.modality or "").strip().upper()
        cand_ev = str(getattr(cand, "evidence_text_span", "") or "").lower().strip()
        cand_obj = str(getattr(cand, "object", "") or "").strip().lower()

        score = 0.0
        s_ok = _check_subj(cand_subj, gold_subj_lower)
        if s_ok:
            score += 10.0
        p_ok = _check_pred(cand_pred, gold_pred_lower)
        if p_ok:
            score += 10.0
        m_ok = (cand_mod == gold_mod)
        if m_ok:
            score += 5.0

        has_ev = False
        if gold_quote and cand_ev:
            if gold_quote in cand_ev or cand_ev in gold_quote:
                score += 100.0
                has_ev = True
            else:
                tok_ov = len(set(gold_quote.split()) & set(cand_ev.split()))
                if tok_ov >= 4:
                    score += 25.0
                    has_ev = True

        gold_obj_toks = set(gold_obj.split())
        cand_obj_toks = set(cand_obj.split())
        obj_ov = len(gold_obj_toks & cand_obj_toks) if (gold_obj_toks and cand_obj_toks) else 0
        has_obj = obj_ov >= min(3, len(gold_obj_toks)) or (cand_obj and cand_obj in gold_obj) or (gold_obj and gold_obj in cand_obj)
        if has_obj:
            score += 10.0

        if (gold_quote or gold_obj) and not (has_ev or has_obj or obj_ov >= 2):
            continue

        if score >= 15.0:
            scored_pairs.append((score, g_idx, c_idx))

scored_pairs.sort(key=lambda x: x[0], reverse=True)

matched_gold = {}
matched_cands = set()

for score, g_idx, c_idx in scored_pairs:
    if g_idx not in matched_gold and c_idx not in matched_cands:
        matched_gold[g_idx] = c_idx
        matched_cands.add(c_idx)

tp = 0
for g_idx, g in enumerate(gold_claims):
    if g_idx in matched_gold:
        cand = res.candidates[matched_gold[g_idx]]
        cand_subj = (cand.subject or "").strip().lower()
        cand_pred = (cand.predicate or "").strip().lower()
        cand_obj = str(cand.object or "").strip().lower()
        cand_mod = str(cand.modality or "").strip().upper()
        
        s_ok = _check_subj(cand_subj, g["subject"].strip().lower())
        p_ok = _check_pred(cand_pred, g["predicate"].strip().lower())
        m_ok = (cand_mod == g["modality"].strip().upper())
        gold_obj_tokens = set(g["object"].lower().split())
        cand_obj_tokens = set(cand_obj.split())
        obj_overlap = len(gold_obj_tokens & cand_obj_tokens) if (gold_obj_tokens and cand_obj_tokens) else 0
        o_ok = obj_overlap >= min(3, len(gold_obj_tokens)) or cand_obj in g["object"].lower() or g["object"].lower() in cand_obj
        if s_ok and p_ok and m_ok and o_ok:
            tp += 1

fp = len(res.candidates) - len(matched_cands)
fn = len(gold_claims) - tp
prec = tp / max(tp + fp, 1)
rec = tp / max(len(gold_claims), 1)
f1 = 2 * prec * rec / max(prec + rec, 1e-9)

print(f"Best-First Matching on EFF-001: Gold={len(gold_claims)}, Cand={len(res.candidates)}, TP={tp}, FP={fp}, FN={fn} | Prec={prec*100:.1f}%, Rec={rec*100:.1f}%, F1={f1*100:.1f}%")
