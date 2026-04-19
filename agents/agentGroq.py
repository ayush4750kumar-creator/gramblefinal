"""
agentGroq.py — Parallel Groq AI Sentiment + Summary
Uses 10 Groq API keys in parallel for fast processing.
Each article gets: sentiment_label, sentiment_reason, summary_60w
Articles are marked is_ready=true only after processing.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import update_article
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# Load all 10 API keys
GROQ_KEYS = [
    os.environ.get(f"GROQ_API_KEY_{i}", "")
    for i in range(1, 11)
]
GROQ_KEYS = [k for k in GROQ_KEYS if k]  # remove empty


def groq_call(api_key: str, prompt: str, max_tokens: int = 200) -> str:
    """Single Groq API call using a specific key."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=15)
        if r.status_code == 429:
            time.sleep(5)
            return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq error: {e}")
        return ""


def process_article(args):
    """Process a single article — sentiment + summary in one Groq call."""
    article, api_key = args
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

    raw = groq_call(api_key, prompt, max_tokens=200)
    if not raw:
        return article["id"], None

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            label = data.get("sentiment", "neutral").lower()
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"
            return article["id"], {
                "sentiment_label":  label,
                "sentiment_reason": data.get("reason", ""),
                "summary_60w":      data.get("summary", ""),
                "is_ready":         True,
            }
    except Exception as e:
        print(f"  ⚠ JSON parse error: {e}")

    return article["id"], None


def run(articles: list) -> int:
    """
    Process a list of articles using 10 Groq keys in parallel.
    Each article gets sentiment + summary, then marked is_ready=true.
    Returns number of articles successfully processed.
    """
    print(f"🤖 AgentGroq — Processing {len(articles)} articles with {len(GROQ_KEYS)} parallel keys")

    if not GROQ_KEYS:
        print("  ⚠ No Groq API keys found — skipping")
        return 0

    if not articles:
        print("  ℹ  Nothing to process.")
        return 0

    # Assign keys round-robin to articles
    tasks = [
        (article, GROQ_KEYS[i % len(GROQ_KEYS)])
        for i, article in enumerate(articles)
    ]

    done = 0
    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}

    with ThreadPoolExecutor(max_workers=len(GROQ_KEYS)) as executor:
        futures = {executor.submit(process_article, task): task for task in tasks}
        for future in as_completed(futures):
            try:
                article_id, result = future.result()
                if result:
                    update_article(article_id, result)
                    counts[result["sentiment_label"]] += 1
                    done += 1
                else:
                    counts["failed"] += 1
                    # Still mark as ready so it shows on website
                    update_article(article_id, {"is_ready": True})
            except Exception as e:
                print(f"  ⚠ Article processing error: {e}")
                counts["failed"] += 1

    print(
        f"  ✅ AgentGroq done — {done}/{len(articles)} processed | "
        f"🟢 {counts['bullish']} bullish | "
        f"🔴 {counts['bearish']} bearish | "
        f"⚪ {counts['neutral']} neutral | "
        f"❌ {counts['failed']} failed\n"
    )
    return done