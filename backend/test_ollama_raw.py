import httpx
import json
import time

url = "http://localhost:11434/api/chat"

print("Test 1: Standard call with format='json'")
start = time.time()
res = httpx.post(url, json={
    "model": "qwen3:1.7b",
    "messages": [
        {"role": "system", "content": "Extract factual claims as a JSON object with key 'claims'. Do not output reasoning or thinking text."},
        {"role": "user", "content": "Customers must request refunds within 30 days of purchase. Enterprise customers receive a 60-day refund window."}
    ],
    "format": "json",
    "stream": False,
    "options": {
        "temperature": 0.0,
        "num_predict": 1024
    }
}, timeout=60)
elapsed = time.time() - start
print(f"Test 1 finished in {elapsed:.2f}s")
print("Response content:")
print(res.json()["message"]["content"])
