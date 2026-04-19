"""
agentGroq.py — Groq AI Sentiment & Summary
Uses Groq's llama3-8b-8192 model (free tier) to generate:
  • sentiment_label  → 'bullish' | 'bearish' | 'neutral'
  • sentiment_reason → 1-sentence explanation
  • summary_20       → 60-word summary
  • opinion          → analyst-style 1-line take

Rate limits (Groq free tier):
  • 30 requests/minute
  • 14,400 requests/day
We cap at 25 req/min and 200/run to stay safe.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_sentiment, get_pending_summary, update_article
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"

# ── Rate limit config ─────────────────────────────────────────────────────────
MAX_PER_MINUTE  = 25     # stay under Groq's 30/min limit
MAX_PER_RUN     = 200    # max articles per pipeline run
RETRY_WAIT      = 65     # seconds to wait if rate limited
MIN_DELAY       = 60 / MAX_PER_MINUTE   # ~2.4s between calls

_call_count   = 0
_window_start = time.time()

def _rate_limit():
    """Ensure we don't exceed MAX_PER_MINUTE calls per minute."""
    global _call_count, _window_start
    now = time.time()
    if now - _window_start >= 60:
        _call_count   = 0
        _window_start = now
    if _call_count >= MAX_PER_MINUTE:
        sleep_for = 60 - (now - _window_start) + 1
        print(f"  ⏳ Groq rate limit — sleeping {sleep_for:.0f}s")
        time.sleep(sleep_for)
        _call_count   = 0
        _window_start = time.time()
    _call_count += 1
    time.sleep(MIN_DELAY)  # gentle pacing


def groq_call(prompt: str, max_tokens: int = 120) -> str:
    """Make a single Groq API call. Returns text or empty string on failure."""
    if not GROQ_API_KEY:
        return ""
    _rate_limit()
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model":       GROQ_MODEL,
        "max_tokens":  max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=15)
        if r.status_code == 429:
            print(f"  ⚠ Groq 429 — waiting {RETRY_WAIT}s")
            time.sleep(RETRY_WAIT)
            return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq call failed: {e}")
        return ""


def analyse_article(title: str, text: str) -> dict:
    """
    Returns dict with keys:
      sentiment_label, sentiment_reason, summary, opinion
    """
    combined = (title or "").strip()
    if text and len(text) > 50:
        combined += "\n\n" + text[:1500]

    prompt = f"""You are a financial news analyst. Analyse this article and respond ONLY with a JSON object, no other text.

Article:
{combined}

Respond with exactly this JSON structure:
{{
  "sentiment": "bullish" or "bearish" or "neutral",
  "reason": "One sentence explaining why (max 20 words)",
  "summary": "60-word summary of the key facts and market impact",
  "opinion": "One analyst-style opinion sentence starting with Bullish/Bearish/Neutral:"
}}"""

    raw = groq_call(prompt, max_tokens=200)
    if not raw:
        return {}

    # Parse JSON from response
    try:
        # Strip markdown code fences if present
        clean = raw.replace("```json", "").replace("```", "").strip()
        # Find JSON object
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            return {
                "sentiment_label":  data.get("sentiment", "neutral"),
                "sentiment_reason": data.get("reason", ""),
                "summary":          data.get("summary", ""),
                "opinion":          data.get("opinion", ""),
            }
    except Exception as e:
        print(f"  ⚠ JSON parse error: {e} | raw: {raw[:100]}")
    return {}


def run_sentiment(limit: int = 100) -> int:
    """Run Groq sentiment on articles missing sentiment."""
    if not GROQ_API_KEY:
        print("  ⚠ GROQ_API_KEY not set — skipping Groq sentiment")
        return 0

    articles = get_pending_sentiment(min(limit, MAX_PER_RUN))
    if not articles:
        print("  ℹ  Nothing needing Groq sentiment.")
        return 0

    print(f"  🤖 Groq sentiment: processing {len(articles)} articles...")
    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}

    for art in articles:
        result = analyse_article(art.get("title", ""), art.get("full_text", ""))
        if not result:
            counts["failed"] += 1
            continue

        label = result.get("sentiment_label", "neutral")
        update_article(art["id"], {
            "sentiment_label":  label,
            "sentiment_reason": result.get("sentiment_reason", ""),
            # Map to existing DB columns
            "sentiment":        "▲" if label == "bullish" else ("▼" if label == "bearish" else "–"),
        })

        # Also save summary + opinion if we got them and article needs it
        if result.get("summary") and not art.get("full_text", "")[:10]:
            update_article(art["id"], {"summary_60w": result["summary"]})
        if result.get("opinion"):
            update_article(art["id"], {"opinion": result["opinion"]})

        counts[label] = counts.get(label, 0) + 1

    total = sum(v for k, v in counts.items() if k != "failed")
    print(
        f"  ✅ Groq sentiment done: 🟢 {counts['bullish']} bullish | "
        f"🔴 {counts['bearish']} bearish | ⚪ {counts['neutral']} neutral | "
        f"❌ {counts['failed']} failed"
    )
    return total


def run_summary(limit: int = 100) -> int:
    """Run Groq summary on articles missing summary."""
    if not GROQ_API_KEY:
        print("  ⚠ GROQ_API_KEY not set — skipping Groq summary")
        return 0

    articles = get_pending_summary(min(limit, MAX_PER_RUN))
    if not articles:
        print("  ℹ  Nothing needing Groq summary.")
        return 0

    print(f"  🤖 Groq summary: processing {len(articles)} articles...")
    done = 0

    for art in articles:
        title = art.get("title", "")
        text  = art.get("full_text", "") or title

        prompt = f"""Summarise this financial news article in exactly 60 words or fewer. 
Be factual, mention company names, numbers, and market impact. No fluff.

Article: {title}
{text[:1000]}

Write only the summary, nothing else:"""

        summary = groq_call(prompt, max_tokens=100)
        if summary:
            update_article(art["id"], {"summary_60w": summary})
            done += 1

    print(f"  ✅ Groq summary done: {done}/{len(articles)} summarised")
    return done


def run(sentiment_limit: int = 80, summary_limit: int = 80) -> int:
    """Run both sentiment and summary. Called from pipeline."""
    print("🤖 AgentGroq — AI Sentiment & Summary (Groq)")
    total = 0
    total += run_sentiment(sentiment_limit)
    total += run_summary(summary_limit)
    print(f"  ✅ AgentGroq done — {total} articles processed\n")
    return total


if __name__ == "__main__":
    run()
