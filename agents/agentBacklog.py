"""
agentBacklog.py — Parallel Backlog Processor (FIXED v3)

Changes from v2:
- Now accepts an optional `pool` parameter (GroqKeyPool) in run()
- MAIN_POOL is the default → main pipeline behaviour unchanged
- SEARCH_POOL is passed in by run_for_symbol() → search uses its own 3 keys
- Internal key loading kept as fallback if groq_pool is unavailable
"""
import sys, os, time, json, threading, re, unicodedata
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_conn
from groq_pool import MAIN_POOL, GroqKeyPool
import requests
import psycopg2.extras

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


# ── Content sanitizer ─────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    """Remove null bytes, non-printable chars, and normalize unicode."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Cc" or c in ("\n", "\t")
    )
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Full-text scraper ─────────────────────────────────────────────────────────

def scrape_article_text(url: str) -> str:
    """Fetch the actual article page and extract readable text."""
    if not url:
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return ""
        text = r.text
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>',  ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:5000]
    except Exception:
        return ""


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


# ── Groq call — exponential backoff + key-death detection ────────────────────

def groq_call(key: str, prompt: str, agent_id: int) -> str:
    consecutive_429 = 0
    for attempt in range(12):
        try:
            r = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       GROQ_MODEL,
                    "max_tokens":  300,
                    "temperature": 0.2,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=25,
            )

            if r.status_code == 400:
                print(f"  ❌ Agent {agent_id}: 400 Bad Request — {r.text[:400]}")
                return ""

            if r.status_code == 429:
                consecutive_429 += 1
                retry_after = float(r.headers.get("retry-after", 0))
                wait = max(retry_after, min(2 ** consecutive_429, 60))
                print(f"  ⏳ Agent {agent_id}: rate limited (429), waiting {wait:.0f}s "
                      f"[attempt {attempt+1}/12]")
                if consecutive_429 >= 3:
                    print(f"  💀 Agent {agent_id}: key exhausted — 3 consecutive 429s")
                    return "KEY_EXHAUSTED"
                time.sleep(wait)
                continue

            consecutive_429 = 0
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            print(f"  ⏱ Agent {agent_id}: timeout (attempt {attempt+1})")
            time.sleep(3)
        except Exception as e:
            print(f"  ❌ Agent {agent_id}: error — {e} (attempt {attempt+1})")
            time.sleep(3)
    return ""


# ── Process one article ───────────────────────────────────────────────────────

def process_one(key: str, article: dict, agent_id: int):
    title = article.get("title", "")     or ""
    text  = article.get("full_text", "") or ""
    url   = article.get("url", "")       or ""

    title = sanitize(title)
    text  = sanitize(text)

    if len(text.strip()) < 200 and url:
        print(f"  🌐 Agent {agent_id}: scraping article {article['id']}")
        scraped = scrape_article_text(url)
        if scraped:
            text = sanitize(scraped)
            try:
                with _db_lock:
                    conn = get_conn()
                    cur  = conn.cursor()
                    cur.execute(
                        "UPDATE articles SET full_text=%s WHERE id=%s",
                        (text[:8000], article["id"])
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
            except Exception:
                pass

    combined = sanitize((title + "\n\n" + text[:3000]).strip())

    if not combined or len(combined) < 20:
        print(f"  ⚠ Agent {agent_id}: article {article['id']} has no content — skipping")
        return None

    prompt = f"""You are a financial news analyst. Analyse this article and respond ONLY with a JSON object — no markdown, no explanation.

Article:
{combined}

Respond with exactly this JSON (nothing else):
{{
  "sentiment": "bullish" or "bearish" or "neutral",
  "reason": "one sentence, max 15 words, explaining why",
  "summary": "between 40 and 60 words covering key facts, numbers, and market impact"
}}

CRITICAL RULES:
- summary MUST be 40-60 words
- sentiment MUST be one of: bullish, bearish, neutral
- Output ONLY the JSON, no other text"""

    raw = groq_call(key, prompt, agent_id)

    if raw == "KEY_EXHAUSTED":
        return "KEY_EXHAUSTED"

    if not raw:
        print(f"  ❌ Agent {agent_id}: empty response for article {article['id']}")
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
                padded  = (title + ". " + summary).strip()
                words   = padded.split()
                summary = " ".join(words[:60]) if len(words) > 60 else padded

            reason = data.get("reason", "").strip() or f"{label.capitalize()} signal detected."

            return {
                "id":               article["id"],
                "sentiment_label":  label,
                "sentiment_reason": reason,
                "summary_60w":      summary,
            }
        else:
            print(f"  ❌ Agent {agent_id}: no JSON in response for article {article['id']}")
            print(f"     Raw: {raw[:150]}")

    except json.JSONDecodeError as e:
        print(f"  ❌ Agent {agent_id}: JSON parse error article {article['id']}: {e}")
        print(f"     Raw: {raw[:150]}")
    except Exception as e:
        print(f"  ❌ Agent {agent_id}: unexpected error article {article['id']}: {e}")

    return None


# ── Sub-agent: owns one key, drains from shared queue ────────────────────────

def sub_agent(agent_id: int, key: str, queue: ArticleQueue,
              counts: dict, lock: threading.Lock):
    while True:
        article = queue.pop()
        if article is None:
            break

        result = process_one(key, article, agent_id)

        if result == "KEY_EXHAUSTED":
            with queue._lock:
                queue._items.insert(0, article)
            print(f"  🔄 Agent {agent_id}: returned article {article['id']} to queue, stopping")
            break

        if result:
            save_result(result)
            with lock:
                counts["done"] += 1
                counts[result["sentiment_label"]] += 1
        else:
            with lock:
                counts["failed"] += 1

        time.sleep(1.5)


# ── Fetch backlog from DB ─────────────────────────────────────────────────────

def get_backlog() -> list:
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text, url FROM articles
        WHERE (summary_60w IS NULL OR summary_60w = '')
        AND (is_duplicate IS NULL OR is_duplicate = false)
        AND created_at > NOW() - INTERVAL '6 days'
        ORDER BY created_at DESC LIMIT 100
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ── Main run ──────────────────────────────────────────────────────────────────

def run(pool: GroqKeyPool = MAIN_POOL) -> int:
    """
    Process the article backlog using the given key pool.

    - Called with no args by run_once()       → uses MAIN_POOL (8 keys)
    - Called with SEARCH_POOL by run_for_symbol() → uses search keys (3 keys)
    """
    # Extract keys from the pool
    keys = pool._keys
    if not keys or keys == ["placeholder"]:
        print("  ⚠ AgentBacklog — No Groq keys found in pool")
        return 0

    articles = get_backlog()
    if not articles:
        print("  ✅ AgentBacklog — No backlog!")
        return 0

    n_agents = len(keys)
    pool_name = "SEARCH" if pool is not MAIN_POOL else "MAIN"
    print(f"📦 AgentBacklog — {len(articles)} articles | {n_agents} sub-agents | pool={pool_name}")

    queue  = ArticleQueue(articles)
    counts = {"done": 0, "bullish": 0, "bearish": 0, "neutral": 0, "failed": 0}
    lock   = threading.Lock()
    total  = len(articles)

    threads = []
    for i, key in enumerate(keys):
        t = threading.Thread(
            target=sub_agent,
            args=(i + 1, key, queue, counts, lock),
            daemon=True,
        )
        threads.append(t)
        t.start()
        time.sleep(0.3)

    start = time.time()
    while any(t.is_alive() for t in threads):
        time.sleep(10)
        with lock:
            done = counts["done"] + counts["failed"]
        elapsed   = time.time() - start
        rate      = done / elapsed if elapsed > 0 else 0
        remaining = total - done
        eta       = remaining / rate if rate > 0 else 0
        print(f"  📦 Backlog: {done}/{total} | ✅{counts['done']} ❌{counts['failed']} "
              f"| {rate:.1f}/s | ETA {eta:.0f}s")

    for t in threads:
        t.join()

    elapsed = time.time() - start
    print(
        f"  ✅ AgentBacklog done — {counts['done']}/{total} in {elapsed:.0f}s | "
        f"🟢 {counts['bullish']} | 🔴 {counts['bearish']} | "
        f"⚪ {counts['neutral']} | ❌ {counts['failed']}\n"
    )
    return counts["done"]