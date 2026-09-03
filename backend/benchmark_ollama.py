import httpx
import time
import json

url = 'http://localhost:11434/api/chat'

# Test standard prompt
prompt = 'Extract atomic claims from this text: Customers must request refunds within 30 days. Enterprise customers get 60 days. Return JSON array under "claims".'

print("Sending request to Ollama (qwen3:1.7b)...")
start = time.time()
try:
    res = httpx.post(url, json={
        "model": "qwen3:1.7b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_ctx": 1024, "num_predict": 256}
    }, timeout=120)
    elapsed = time.time() - start
    print(f"Status: {res.status_code} in {elapsed:.2f}s")
    if res.status_code == 200:
        print("Response content:")
        print(res.json()["message"]["content"][:500])
except Exception as e:
        print("Error:", e)
