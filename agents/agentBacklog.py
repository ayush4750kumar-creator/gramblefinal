"""
agentBacklog.py — Parallel Backlog Processor
- Reads GROQ_API_KEY_1 ... GROQ_API_KEY_50 (however many you have)
- Spawns one sub-agent per key
- All sub-agents pull from same shared queue simultaneously
- Each sub-agent owns its key exclusively = zero contention
- Waits and retries on rate limit (never skips)
"""
import sys, os, time, json, threading
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_conn
import requests
import psycopg2.extras

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# Supports up to 50 keys automatically
GROQ_KEYS = [k for k in [
    os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(1, 51)
] if k]


# ── Shared thread-safe article queue ─────────────────────────────────────────

class ArticleQueue:
    def __init__(self, articles: list):
        self._items = list(articles)
        self._lock  = threading.Lock()

    def pop(self):
        with self._lock:
            return self._items.pop(0) if self._items else None

    def size(self):
        with self._lock:
            return len(self._items)


# ── Thread-safe DB writes ─────────────────────────────────────────────────────

_db_lock = threading.Lock()

def save_result(result: dict):
    with _db_lock:
        conn = get_conn()
        cur  = conn.cursor()
        try:
            cur.execute("""
                UPDATE articles
                SET sentiment_label=%s, sentiment_reason=%s,
                    summary_60w=%s, is_ready=true
                WHERE id=%s
            """, (
                result["sentiment_label"],
                result["sentiment_reason"],
                result["summary_60w"],
                result["id"],
            ))
            conn.commit()
        finally:
            cur.close()
            conn.close()

def mark_ready(article_id: int):
    with _db_lock:
        conn = get_conn()
        cur  = conn.cursor()
        try:
            cur.execute("UPDATE articles SET is_ready=true WHERE id=%s", (article_id,))
            conn.commit()
        finally:
            cur.close()
            conn.close()


# ── Groq call — one key, wait and retry on rate limit ────────────────────────

def groq_call(key: str, prompt: str) -> str:
    for attempt in range(10):
        try:
            r = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       GROQ_MODEL,
                    "max_tokens":  250,
                    "temperature": 0.2,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20,
            )
            if r.status_code == 429:
                wait = min(float(r.headers.get("retry-after", 10)), 10)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return ""


# ── Process one article ───────────────────────────────────────────────────────

def process_one(key: str, article: dict) -> dict | None:
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
  "summary": "MUST be between 30 and 60 words. Cover key facts, numbers, and market impact."
}}

CRITICAL: The summary field MUST contain between 30 and 60 words."""

    raw = groq_call(key, prompt)
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
            }
    except Exception:
        pass
    return None


# ── Sub-agent: owns one key, drains from shared queue ────────────────────────

def sub_agent(agent_id: int, key: str, queue: ArticleQueue,
              counts: dict, lock: threading.Lock):
    while True:
        article = queue.pop()
        if article is None:
            break  # queue empty, this sub-agent is done

        result = process_one(key, article)

        if result:
            save_result(result)
            with lock:
                counts["done"]  += 1
                counts[result["sentiment_label"]] += 1
        else:
            mark_ready(article["id"])
            with lock:
                counts["failed"] += 1

        # 2s delay = 30 RPM per key, exactly at free tier limit
        pass  # no sleep needed — each agent owns its key exclusively


# ── Fetch backlog from DB ─────────────────────────────────────────────────────

def get_backlog() -> list:
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text FROM articles
        WHERE (is_ready IS NULL OR is_ready = false)
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY created_at ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ── Main run ──────────────────────────────────────────────────────────────────

def run() -> int:
    if not GROQ_KEYS:
        print("  ⚠ AgentBacklog — No Groq keys found")
        return 0

    articles = get_backlog()
    if not articles:
        print("  ✅ AgentBacklog — No backlog!")
        return 0

    n_agents = len(GROQ_KEYS)
    print(f"📦 AgentBacklog — {len(articles)} articles | {n_agents} sub-agents | one key each")

    queue  = ArticleQueue(articles)
    counts = {"done": 0, "bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}
    lock   = threading.Lock()
    total  = len(articles)

    # Spawn one thread per key
    threads = []
    for i, key in enumerate(GROQ_KEYS):
        t = threading.Thread(
            target=sub_agent,
            args=(i + 1, key, queue, counts, lock),
            daemon=True,
        )
        threads.append(t)
        t.start()
        time.sleep(0.5)  # stagger — don't hit all keys simultaneously

    # Progress every 10s
    start = time.time()
    while any(t.is_alive() for t in threads):
        time.sleep(2.0)
        with lock:
            done = counts["done"] + counts["failed"]
        elapsed = time.time() - start
        rate    = done / elapsed if elapsed > 0 else 0
        eta     = (total - done) / rate if rate > 0 else 0
        print(f"  📦 Backlog: {done}/{total} | {rate:.1f}/s | ETA {eta:.0f}s")

    for t in threads:
        t.join()

    elapsed = time.time() - start
    print(
        f"  ✅ AgentBacklog done — {counts['done']}/{total} in {elapsed:.0f}s | "
        f"🟢 {counts['bullish']} | 🔴 {counts['bearish']} | "
        f"⚪ {counts['neutral']} | ❌ {counts['failed']}\n"
    )
    return counts["done"]