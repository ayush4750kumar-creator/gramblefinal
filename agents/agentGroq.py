"""
agentGroq.py — Groq AI Sentiment + Summary with retry
Rotates through 10 keys, retries on rate limit, marks is_ready=true.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import update_article
import requests

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

GROQ_KEYS = [k for k in [
    os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(1, 11)
] if k]

print(f"  🔑 Loaded {len(GROQ_KEYS)} Groq keys")


def groq_call_with_retry(prompt: str, max_tokens: int = 200) -> str:
    """Try all keys with retries until one works."""
    
    # Try each key
    for attempt in range(3):  # 3 full rotations through all keys
        for i, key in enumerate(GROQ_KEYS):
            try:
                r = requests.post(GROQ_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.2,
                          "messages": [{"role": "user", "content": prompt}]},
                    timeout=20
                )
                if r.status_code == 429:
                    # This key is rate limited, try next
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                continue
        
        # All keys failed this round, wait before retry
        if attempt < 2:
            wait = 10 * (attempt + 1)
            print(f"  ⏳ All keys rate limited — waiting {wait}s (attempt {attempt+1}/3)")
            time.sleep(wait)
    
    return ""


def process_article(article) -> dict:
    title = article.get("title", "") or ""
    text  = article.get("full_text", "") or ""
    combined = title + "\n\n" + text[:1200]

    prompt = f"""You are a financial news analyst. Analyse this article and respond ONLY with a JSON object.

Article:
{combined}

Respond with exactly this JSON:
{{
  "sentiment": "bullish" or "bearish" or "neutral",
  "reason": "one sentence max 15 words explaining why",
  "summary": "summary of key facts and market impact in 60 words or fewer"
}}"""

    raw = groq_call_with_retry(prompt, max_tokens=200)
    if not raw:
        return None

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            label = data.get("sentiment", "neutral").lower()
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"
            return {
                "sentiment_label":  label,
                "sentiment_reason": data.get("reason", ""),
                "summary_60w":      data.get("summary", ""),
                "is_ready":         True,
            }
    except Exception as e:
        print(f"  ⚠ JSON parse error: {e}")

    return None


def run(articles: list) -> int:
    print(f"🤖 AgentGroq — Processing {len(articles)} articles with {len(GROQ_KEYS)} keys")

    if not GROQ_KEYS:
        print("  ⚠ No Groq API keys — marking all ready without AI")
        for art in articles:
            update_article(art["id"], {"is_ready": True})
        return 0

    if not articles:
        print("  ℹ  Nothing to process.")
        return 0

    done = 0
    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}

    for idx, article in enumerate(articles):
        result = process_article(article)
        if result:
            update_article(article["id"], result)
            counts[result["sentiment_label"]] += 1
            done += 1
        else:
            counts["failed"] += 1
            # Still mark ready so it shows on website
            update_article(article["id"], {"is_ready": True})

        # Progress every 20 articles
        if (idx + 1) % 20 == 0:
            print(f"  📊 Progress: {idx+1}/{len(articles)} done")

    print(
        f"  ✅ AgentGroq done — {done}/{len(articles)} processed | "
        f"🟢 {counts['bullish']} bullish | "
        f"🔴 {counts['bearish']} bearish | "
        f"⚪ {counts['neutral']} neutral | "
        f"❌ {counts['failed']} failed\n"
    )
    return done