"""
agentBacklog.py — Parallel Backlog Processor (v7)

Changes from v6:
- Smart image resolution: symbol-based Pexels query
- Logo blacklist — skips yahoo/google/bing/reuters logos
- og:image only used if it looks like a real photo
"""
import sys, os, time, json, threading, re, unicodedata
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_conn
from groq_pool import MAIN_POOL, GroqKeyPool
import requests
import psycopg2.extras

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_URL = "https://api.pexels.com/v1/search"

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Words in og:image URLs that indicate a logo/brand image — skip these
LOGO_BLACKLIST = [
    'logo', 'icon', 'brand', 'favicon', 'avatar', 'placeholder',
    'yahoo', 'google', 'bing', 'reuters', 'bloomberg', 'moneycontrol',
    'economictimes', 'ndtv', 'livemint', 'businessstandard', 'cnbc',
    'marketwatch', 'seekingalpha', 'default', 'fallback', 'no-image',
    'noimage', 'blank', 'header', 'banner-logo', 'site-logo',
]

# Symbol → readable Pexels search query
SYMBOL_MAP = {
    "AAPL":           "Apple technology iPhone",
    "NVDA":           "Nvidia GPU chip AI",
    "GOOGL":          "Google office technology",
    "META":           "Meta Facebook social media",
    "AMZN":           "Amazon warehouse delivery",
    "MSFT":           "Microsoft office software",
    "TSLA":           "Tesla electric car",
    "INTC":           "Intel semiconductor chip",
    "AMD":            "AMD processor chip",
    "NFLX":           "Netflix streaming",
    "UBER":           "Uber ride sharing",
    "COIN":           "Coinbase cryptocurrency bitcoin",
    "PLTR":           "Palantir data analytics",
    "SHOP":           "Shopify ecommerce",
    "JPM":            "JPMorgan bank Wall Street",
    "BAC":            "Bank of America finance",
    "GS":             "Goldman Sachs finance",
    "INFY":           "Infosys India office technology",
    "TCS":            "Tata Consultancy Services India",
    "HDFCBANK":       "HDFC Bank India finance",
    "ICICIBANK":      "ICICI Bank India",
    "SBIN":           "State Bank of India",
    "RELIANCE":       "Reliance Industries India",
    "WIPRO":          "Wipro India technology",
    "ITC":            "ITC India consumer goods",
    "INDUSINDBK.NS":  "IndusInd Bank India",
    "COCHINSHIP.BO":  "Cochin Shipyard India ship",
    "ADANIENT":       "Adani Enterprises India",
    "TATAMOTORS":     "Tata Motors car India",
    "BAJFINANCE":     "Bajaj Finance India",
    "HINDUNILVR":     "Hindustan Unilever India",
    "KOTAKBANK":      "Kotak Mahindra Bank India",
    "AXISBANK":       "Axis Bank India",
    "MARUTI":         "Maruti Suzuki car India",
    "SUNPHARMA":      "Sun Pharma medicine India",
    "NTPC":           "NTPC power plant India",
    "ONGC":           "ONGC oil India",
    "TATASTEEL":      "Tata Steel industry",
    "JSWSTEEL":       "JSW Steel industry",
    "TITAN":          "Titan watches jewelry India",
    "NESTLEIND":      "Nestle food India",
    "HCLTECH":        "HCL Technologies India",
    "TECHM":          "Tech Mahindra India",
    "ZOMATO":         "Zomato food delivery India",
    "PAYTM":          "Paytm digital payment India",
    "NYKAA":          "Nykaa beauty India",
    "INDIGO":         "IndiGo airline India",
    "IRCTC":          "IRCTC Indian railway",
    "DRREDDY":        "Dr Reddys pharmacy India",
    "CIPLA":          "Cipla medicine India",
    "APOLLOHOSP":     "Apollo Hospital India",
}


def sanitize(text: str) -> str:
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


# ── Scrape article: returns text + og:image ───────────────────────────────────

def scrape_article(url: str) -> dict:
    if not url:
        return {"text": "", "image": None}
    try:
        r = requests.get(url, headers=SCRAPE_HEADERS, timeout=10)
        if r.status_code != 200:
            return {"text": "", "image": None}

        html = r.text

        # grab og:image
        image = None
        og = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
            html, re.IGNORECASE
        )
        if not og:
            og = re.search(
                r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']',
                html, re.IGNORECASE
            )
        if not og:
            og = re.search(
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
                html, re.IGNORECASE
            )
        if og:
            image = og.group(1).strip()

        # strip html for text
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>',   ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return {"text": text[:5000], "image": image}

    except Exception:
        return {"text": "", "image": None}


# ── Image helpers ─────────────────────────────────────────────────────────────

def is_real_image(url: str) -> bool:
    """Returns False if the URL looks like a logo/brand/placeholder."""
    if not url:
        return False
    url_lower = url.lower()
    return not any(word in url_lower for word in LOGO_BLACKLIST)


def get_pexels_image(query: str) -> str | None:
    """Search Pexels. Returns landscape image URL or None."""
    if not PEXELS_KEY or not query:
        return None
    try:
        r = requests.get(
            PEXELS_URL,
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=8,
        )
        if r.status_code != 200:
            return None
        photos = r.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
        return None
    except Exception:
        return None


def resolve_image(article: dict, scraped_image: str | None) -> str | None:
    """
    Priority:
    1. Already has image_url in DB → skip (return None = no update)
    2. og:image looks like a real photo → use it
    3. Pexels with symbol/company name → use it
    4. None → frontend placeholder
    """
    if article.get("image_url"):
        return None  # already set, no update needed

    # og:image only if it's a real photo not a logo
    if scraped_image and is_real_image(scraped_image):
        return scraped_image

    # Pexels — use symbol map first, fall back to raw symbol
    symbol = (article.get("symbol") or "").upper().strip()
    pexels_query = SYMBOL_MAP.get(
        symbol,
        f"{symbol} stock market finance" if symbol else "stock market finance"
    )
    return get_pexels_image(pexels_query)


# ── DB helpers ────────────────────────────────────────────────────────────────

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


_db_lock = threading.Lock()


def save_result(result: dict):
    with _db_lock:
        conn = get_conn()
        cur  = conn.cursor()
        try:
            if result.get("image_url"):
                cur.execute("""
                    UPDATE articles
                    SET sentiment_label=%s, sentiment_reason=%s,
                        summary_60w=%s, image_url=%s, is_ready=true
                    WHERE id=%s
                """, (
                    result["sentiment_label"],
                    result["sentiment_reason"],
                    result["summary_60w"],
                    result["image_url"],
                    result["id"],
                ))
            else:
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


# ── Groq call ─────────────────────────────────────────────────────────────────

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

    scraped_image = None

    if len(text.strip()) < 200 and url:
        print(f"  🌐 Agent {agent_id}: scraping article {article['id']}")
        scraped = scrape_article(url)
        scraped_image = scraped["image"]

        if scraped["text"]:
            text = sanitize(scraped["text"])
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

    # resolve image
    image_url = resolve_image(article, scraped_image)
    if image_url:
        print(f"  🖼  Agent {agent_id}: image resolved for article {article['id']}")

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
                "image_url":        image_url,
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


# ── Sub agent thread ──────────────────────────────────────────────────────────

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

def get_backlog(symbol: str = None, limit: int = 100) -> list:
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if symbol:
        cur.execute("""
            SELECT id, title, full_text, url, image_url, symbol FROM articles
            WHERE (summary_60w IS NULL OR summary_60w = '')
            AND (is_duplicate IS NULL OR is_duplicate = false)
            AND created_at > NOW() - INTERVAL '6 days'
            AND symbol = %s
            ORDER BY created_at DESC LIMIT %s
        """, (symbol, limit))
    else:
        cur.execute("""
            SELECT id, title, full_text, url, image_url, symbol FROM articles
            WHERE (summary_60w IS NULL OR summary_60w = '')
            AND (is_duplicate IS NULL OR is_duplicate = false)
            AND created_at > NOW() - INTERVAL '6 days'
            ORDER BY created_at DESC LIMIT %s
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


# ── Main run ──────────────────────────────────────────────────────────────────

def run(pool: GroqKeyPool = MAIN_POOL, symbol: str = None, limit: int = 100) -> int:
    keys = pool._keys
    if not keys or keys == ["placeholder"]:
        print("  ⚠ AgentBacklog — No Groq keys found in pool")
        return 0

    articles = get_backlog(symbol=symbol, limit=limit)
    if not articles:
        print("  ✅ AgentBacklog — No backlog!")
        return 0

    n_agents  = len(keys)
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