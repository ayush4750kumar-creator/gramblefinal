import os, requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

for i in range(1, 51):
    key = os.environ.get(f"GROQ_API_KEY_{i}", "")
    if not key:
        continue
    r = requests.post(GROQ_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "llama-3.1-8b-instant", "max_tokens": 10,
              "messages": [{"role": "user", "content": "hi"}]},
        timeout=10)
    print(f"Key {i}: {r.status_code} — {'✅ OK' if r.status_code == 200 else '❌ FAIL'}")
