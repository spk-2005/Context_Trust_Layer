import httpx
import json
import re

prompt = """Do these two claims contradict? Reply ONLY with JSON:
{"is_contradiction":bool,"conflict_type":"direct_contradiction|numerical_discrepancy|temporal_outdated|complementary|compatible","severity":"high|medium|low","confidence":float,"reasoning":"one sentence"}

A: Customers must request refunds within 30 days of purchase.
B: Enterprise customers receive a 60-day refund window.
"""

res = httpx.post("http://localhost:11434/api/chat", json={
    "model": "qwen3:1.7b",
    "messages": [
        {"role": "system", "content": "You are a JSON consistency analyzer. Output JSON only."},
        {"role": "user", "content": prompt}
    ],
    "format": "json",
    "stream": False,
    "options": {
        "temperature": 0.0,
        "num_predict": 512
    }
}, timeout=60)

raw = res.json()["message"]["content"]
print("RAW RESPONSE:")
print(repr(raw))
cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
print("CLEANED RESPONSE:")
print(repr(cleaned))
