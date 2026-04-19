"""
agentGroq.py — Groq AI Sentiment + Summary (optimized)
- Per-key cooldown tracking (no wasted retries on limited keys)
- Concurrent processing with ThreadPoolExecutor
- Batched DB writes (1 connection per batch, not per article)
- Respects Retry-After headers from Groq
"""
import sys, os, time, json, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_conn
import requests
import psycopg2.extras

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

GROQ_KEYS = [k for k in [
    os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(1, 11)
] if k]

print(f"  🔑 Loaded {len(GROQ_KEYS)} Groq keys")


# ── Per-key cooldown tracker ──────────────────────────────────────────────────

class KeyPool:
    """Tracks per-key rate limit cooldowns. Thread-safe."""

    def __init__(self, keys: list[str]):
        self.keys = keys
        # available_at[i] = unix timestamp when key i is usable again
        self._available_at = [0.0] * len(keys)
        self._lock = threading.Lock()

    def get_key(self) -> tuple[int, str] | None:
        """Return (index, key) for the soonest-available key, sleeping if needed."""
        with self._lock:
            now = time.time()
            # Find any immediately available key
            for i, key in enumerate(self.keys):
                if self._available_at[i] <= now:
                    return i, key
            # All limited — find the one that unlocks soonest
            idx = min(range(len(self.keys)), key=lambda i: self._available_at[i])
            wait = self._available_at[idx] - now
        # Sleep outside the lock so other threads aren't blocked
        if wait > 0:
            time.sleep(wait)
        return idx, self.keys[idx]

    def mark_limited(self, idx: int, retry_after: float = 60.0):
        with self._lock:
            # Don't shorten an existing cooldown
            earliest = time.time() + retry_after
            if self._available_at[idx] < earliest:
                self._available_at[idx] = earliest

    def all_cooldown_remaining(self) -> float:
        with self._lock:
            return max(0.0, min(self._available_at) - time.time())


# ── Single Groq call ──────────────────────────────────────────────────────────

def groq_call(pool: KeyPool, prompt: str, max_tokens: int = 200) -> str:
    """
    Make one Groq call, rotating keys and respecting rate limits.
    Retries up to len(keys) * 2 times before giving up.
    """
    max_attempts = len(pool.keys) * 2 or 6

    for attempt in range(max_attempts):
        idx, key = pool.get_key()
        try:
            r = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20,
            )

            if r.status_code == 429:
                # Respect Retry-After if present, default 60s
                retry_after = float(r.headers.get("retry-after", 60))
                pool.mark_limited(idx, retry_after)
                continue  # immediately try next available key

            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            # Don't penalise key for a timeout
            continue
        except Exception:
            continue

    return ""


# ── Per-article processing ────────────────────────────────────────────────────

def process_article(pool: KeyPool, article: dict) -> dict | None:
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

    raw = groq_call(pool, prompt, max_tokens=250)
    if not raw:
        return None

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data    = json.loads(clean[start:end])
            label   = data.get("sentiment", "neutral").lower()
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"

            summary = data.get("summary", "").strip()

            # Hard enforce 30–60 words: trim if over, discard if under
            words = summary.split()
            if len(words) > 60:
                summary = " ".join(words[:60])
            elif len(words) < 30:
                # Too short — build a minimal fallback from title
                summary = (title + " " + summary).strip()
                words = summary.split()
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


# ── Batched DB write ──────────────────────────────────────────────────────────

def flush_results(results: list[dict]):
    """Write a batch of results to DB in a single connection."""
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
                    r.get("is_ready", True),
                    r["id"],
                ),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def mark_ready_batch(article_ids: list[int]):
    """Mark articles as ready without sentiment (fallback)."""
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


# ── Main run ──────────────────────────────────────────────────────────────────

def run(articles: list, max_workers: int = 5, flush_every: int = 20) -> int:
    """
    Process articles concurrently.

    max_workers : how many threads hit Groq in parallel.
                  Keep ≤ number of keys to avoid thrashing.
    flush_every : write results to DB after every N completions.
    """
    print(f"🤖 AgentGroq — Processing {len(articles)} articles with {len(GROQ_KEYS)} keys")

    if not GROQ_KEYS:
        print("  ⚠ No Groq API keys — marking all ready without AI")
        mark_ready_batch([a["id"] for a in articles])
        return 0

    if not articles:
        print("  ℹ  Nothing to process.")
        return 0

    pool   = KeyPool(GROQ_KEYS)
    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}
    done   = 0

    pending_writes: list[dict] = []
    failed_ids:     list[int]  = []
    write_lock = threading.Lock()

    # Limit concurrency to number of keys (no point exceeding it)
    workers = min(max_workers, len(GROQ_KEYS))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_article, pool, art): art
            for art in articles
        }

        completed = 0
        for future in as_completed(futures):
            art    = futures[future]
            result = future.result()
            completed += 1

            with write_lock:
                if result:
                    pending_writes.append(result)
                    counts[result["sentiment_label"]] += 1
                    done += 1
                else:
                    failed_ids.append(art["id"])
                    counts["failed"] += 1

                # Flush to DB every flush_every completions
                if len(pending_writes) >= flush_every:
                    flush_results(pending_writes)
                    pending_writes.clear()

                if completed % 20 == 0:
                    print(f"  📊 Progress: {completed}/{len(articles)} done")

    # Final flush
    flush_results(pending_writes)
    mark_ready_batch(failed_ids)   # mark failures ready so site doesn't stall

    print(
        f"  ✅ AgentGroq done — {done}/{len(articles)} processed | "
        f"🟢 {counts['bullish']} bullish | "
        f"🔴 {counts['bearish']} bearish | "
        f"⚪ {counts['neutral']} neutral | "
        f"❌ {counts['failed']} failed\n"
    )
    return done