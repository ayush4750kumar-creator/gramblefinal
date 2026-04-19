"""
agentGroq.py — Groq AI Sentiment + Summary
- Sequential processing (stable, no threading bugs)
- Per-key cooldown tracking (no wasted waits on limited keys)
- Respects Retry-After headers from Groq
- Batched DB writes every 20 articles
- Summary enforced 30–60 words
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_conn
import requests

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

GROQ_KEYS = [k for k in [
    os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(1, 11)
] if k]

print(f"  🔑 Loaded {len(GROQ_KEYS)} Groq keys")

# Per-key cooldown: index -> unix timestamp when usable again
_key_available_at = [0.0] * len(GROQ_KEYS)


def get_best_key() -> tuple[int, str]:
    """Return (index, key) for the soonest-available key, sleeping only if needed."""
    now = time.time()
    for i, key in enumerate(GROQ_KEYS):
        if _key_available_at[i] <= now:
            return i, key
    # All limited — sleep only until the soonest one unlocks
    idx  = min(range(len(GROQ_KEYS)), key=lambda i: _key_available_at[i])
    wait = _key_available_at[idx] - now
    print(f"  ⏳ All keys rate limited — waiting {wait:.0f}s for key {idx+1} to unlock")
    time.sleep(wait)
    return idx, GROQ_KEYS[idx]


def mark_key_limited(idx: int, retry_after: float = 60.0):
    earliest = time.time() + retry_after
    if _key_available_at[idx] < earliest:
        _key_available_at[idx] = earliest


def groq_call(prompt: str, max_tokens: int = 250) -> str:
    """Try keys smartly — skip limited ones, sleep only for the soonest reset."""
    max_attempts = max(len(GROQ_KEYS) * 2, 6)

    for _ in range(max_attempts):
        idx, key = get_best_key()
        try:
            r = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model":       GROQ_MODEL,
                    "max_tokens":  max_tokens,
                    "temperature": 0.2,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20,
            )

            if r.status_code == 429:
                retry_after = float(r.headers.get("retry-after", 60))
                mark_key_limited(idx, retry_after)
                continue  # immediately try next best key

            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            continue  # don't penalise key for a timeout
        except Exception:
            continue

    return ""


def process_article(article: dict) -> dict | None:
    title    = article.get("title", "") or ""
    text     = article.get("full_text", "") or ""
    combined = (title + "\n\n" + text[:1200]).strip()

    prompt = f"""You are a financial news analyst. Analyse this article and respond ONLY with a JSON object.

Article:
{combined}

Respond with exactly this JSON:
{{
  "sentiment": "bullish" or "bearish" or "neutral",
  "reason": "one sentence max 15 words explaining why",
  "summary": "MUST be between 30 and 60 words. Cover key facts, numbers, and market impact. Do not pad or truncate."
}}

CRITICAL: The summary field MUST contain between 30 and 60 words. Count carefully before responding."""

    raw = groq_call(prompt, max_tokens=250)
    if not raw:
        return None

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data  = json.loads(clean[start:end])
            label = data.get("sentiment", "neutral").lower()
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"

            summary = data.get("summary", "").strip()
            words   = summary.split()

            # Hard enforce 30–60 words
            if len(words) > 60:
                summary = " ".join(words[:60])
            elif len(words) < 30:
                summary = (title + ". " + summary).strip()
                words   = summary.split()
                summary = " ".join(words[:60]) if len(words) > 60 else summary

            return {
                "id":               article["id"],
                "sentiment_label":  label,
                "sentiment_reason": data.get("reason", ""),
                "summary_60w":      summary,
                "is_ready":         True,
            }
    except Exception as e:
        print(f"  ⚠ JSON parse error for article {article['id']}: {e}")

    return None


def flush_results(results: list[dict]):
    """Write a batch of results in one DB connection."""
    if not results:
        return
    conn = get_conn()
    cur  = conn.cursor()
    try:
        for r in results:
            cur.execute(
                """
                UPDATE articles
                SET sentiment_label=%s, sentiment_reason=%s,
                    summary_60w=%s, is_ready=%s
                WHERE id=%s
                """,
                (
                    r.get("sentiment_label"),
                    r.get("sentiment_reason", ""),
                    r.get("summary_60w", ""),
                    True,
                    r["id"],
                ),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def mark_ready_batch(article_ids: list[int]):
    """Mark failed articles ready so the site doesn't stall."""
    if not article_ids:
        return
    conn = get_conn()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE articles SET is_ready=true WHERE id = ANY(%s)",
            (article_ids,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def run(articles: list) -> int:
    print(f"🤖 AgentGroq — Processing {len(articles)} articles with {len(GROQ_KEYS)} keys")

    if not GROQ_KEYS:
        print("  ⚠ No Groq API keys — marking all ready without AI")
        mark_ready_batch([a["id"] for a in articles])
        return 0

    if not articles:
        print("  ℹ  Nothing to process.")
        return 0

    counts     = {"bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}
    done       = 0
    pending    : list[dict] = []
    failed_ids : list[int]  = []
    start_time = time.time()

    # 10 keys × 30 RPM = 300 RPM max. Use 0.4s gap = ~2.5 req/s, safely under limit.
    REQUEST_DELAY = 0.4

    for idx, article in enumerate(articles):
        result = process_article(article)
        time.sleep(REQUEST_DELAY)

        if result:
            pending.append(result)
            counts[result["sentiment_label"]] += 1
            done += 1
        else:
            failed_ids.append(article["id"])
            counts["failed"] += 1

        # Flush to DB every 20 articles (one connection per batch)
        if len(pending) >= 20:
            flush_results(pending)
            pending.clear()

        if (idx + 1) % 20 == 0:
            elapsed = time.time() - start_time
            rate    = (idx + 1) / elapsed
            eta     = (len(articles) - idx - 1) / rate if rate > 0 else 0
            print(f"  📊 Progress: {idx+1}/{len(articles)} | {rate:.1f}/s | ETA {eta:.0f}s")

    # Final flush
    flush_results(pending)
    mark_ready_batch(failed_ids)

    elapsed = time.time() - start_time
    print(
        f"  ✅ AgentGroq done — {done}/{len(articles)} processed in {elapsed:.0f}s | "
        f"🟢 {counts['bullish']} bullish | "
        f"🔴 {counts['bearish']} bearish | "
        f"⚪ {counts['neutral']} neutral | "
        f"❌ {counts['failed']} failed\n"
    )
    return done