"""
news_apis.py — Central News API Module
Integrates 4 free news APIs as additional sources:
  1. Marketaux     (100/day)  — finance-specific, best for stocks ⭐
  2. Currents API  (600/day)  — general news, most generous free tier
  3. GNews API     (100/day)  — structured, good quality
  4. NewsData.io   (200/day)  — solid general news

KEY FIX: All agents previously called fetch_all_apis independently,
causing 8 agents × 4 APIs = 32 calls per run, exhausting daily quotas
in minutes. Now uses a run-level cache — each unique query is only
fetched ONCE per pipeline run regardless of how many agents call it.

Add to .env:
  MARKETAUX_API_KEY=your_key
  CURRENTS_API_KEY=your_key
  GNEWS_API_KEY=your_key
  NEWSDATA_API_KEY=your_key
"""
import os, time, requests, threading
from datetime import datetime, timezone

MARKETAUX_KEY = os.environ.get("MARKETAUX_API_KEY", "")
CURRENTS_KEY  = os.environ.get("CURRENTS_API_KEY", "")
GNEWS_KEY     = os.environ.get("GNEWS_API_KEY", "")
NEWSDATA_KEY  = os.environ.get("NEWSDATA_API_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GrambleBot/1.0)"
}

# ── Run-level cache — reset at the start of each pipeline run ─────────────────
# Prevents multiple agents calling the same API with the same query.
# Each unique query is fetched once and reused by all subsequent callers.
_cache: dict  = {}
_cache_lock   = threading.Lock()

def reset_cache():
    """Call this at the start of each pipeline run (in agentX/orchestrator)."""
    global _cache
    with _cache_lock:
        _cache = {}

def _cached(key: str, fetch_fn):
    """Return cached result if available, otherwise call fetch_fn and cache it."""
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    result = fetch_fn()
    with _cache_lock:
        _cache[key] = result
    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _make_article(symbol, title, url, source, pub, full_text, agent_source) -> dict:
    return {
        "symbol":          symbol,
        "title":           title,
        "url":             url,
        "source":          source,
        "tag_source_name": source,
        "published_at":    pub or _now_iso(),
        "full_text":       (full_text or "")[:3000],
        "tag_feed":        "company" if symbol and symbol != "MARKET" else "global",
        "tag_category":    "news",
        "agent_source":    agent_source,
        "tag_after_hours": 0,
    }


# ── 1. Marketaux ──────────────────────────────────────────────────────────────

def fetch_marketaux(query: str = "", symbol: str = "", agent_source: str = "API",
                    limit: int = 10) -> list:
    if not MARKETAUX_KEY:
        return []
    cache_key = f"marketaux:{symbol}:{query}"

    def _fetch():
        articles = []
        try:
            params = {
                "api_token":       MARKETAUX_KEY,
                "language":        "en",
                "limit":           min(limit, 10),
                "filter_entities": "true",
            }
            if symbol:
                params["symbols"] = symbol
            elif query:
                params["search"] = query

            r = requests.get(
                "https://api.marketaux.com/v1/news/all",
                params=params, timeout=10
            )
            if r.status_code != 200:
                print(f"  ⚠  Marketaux: HTTP {r.status_code}")
                return []

            for item in r.json().get("data", []):
                title = item.get("title", "")
                url   = item.get("url", "")
                if not title or not url:
                    continue
                entities = item.get("entities", [])
                sym = symbol or (entities[0].get("symbol", "") if entities else "")
                pub = (item.get("published_at") or "")[:19].replace("T", " ")
                articles.append(_make_article(
                    sym, title, url, "Marketaux",
                    pub, item.get("description", ""), agent_source
                ))
        except Exception as e:
            print(f"  ⚠  Marketaux error: {e}")
        return articles

    return _cached(cache_key, _fetch)


# ── 2. Currents API ───────────────────────────────────────────────────────────

def fetch_currents(query: str = "", agent_source: str = "API",
                   limit: int = 10) -> list:
    if not CURRENTS_KEY:
        return []
    cache_key = f"currents:{query}"

    def _fetch():
        articles = []
        try:
            params = {
                "apiKey":   CURRENTS_KEY,
                "language": "en",
                "keywords": query or "stock market finance India",
            }
            r = requests.get(
                "https://api.currentsapi.services/v1/search",
                params=params, timeout=10
            )
            if r.status_code != 200:
                print(f"  ⚠  Currents API: HTTP {r.status_code}")
                return []

            for item in r.json().get("news", [])[:limit]:
                title = item.get("title", "")
                url   = item.get("url", "")
                if not title or not url:
                    continue
                pub = (item.get("published", "") or "")[:19].replace("T", " ")
                articles.append(_make_article(
                    "", title, url, "Currents API",
                    pub, item.get("description", ""), agent_source
                ))
        except Exception as e:
            print(f"  ⚠  Currents API error: {e}")
        return articles

    return _cached(cache_key, _fetch)


# ── 3. GNews API ──────────────────────────────────────────────────────────────

def fetch_gnews(query: str = "", symbol: str = "", agent_source: str = "API",
                limit: int = 10) -> list:
    if not GNEWS_KEY:
        return []
    cache_key = f"gnews:{symbol}:{query}"

    def _fetch():
        articles = []
        try:
            q = query or (f"{symbol} stock" if symbol else "stock market India")
            params = {
                "token":   GNEWS_KEY,
                "q":       q,
                "lang":    "en",
                "country": "in",
                "max":     min(limit, 10),
            }
            r = requests.get(
                "https://gnews.io/api/v4/search",
                params=params, timeout=10
            )
            if r.status_code != 200:
                print(f"  ⚠  GNews API: HTTP {r.status_code}")
                return []

            for item in r.json().get("articles", []):
                title = item.get("title", "")
                url   = item.get("url", "")
                if not title or not url:
                    continue
                pub = (item.get("publishedAt", "") or "")[:19].replace("T", " ")
                articles.append(_make_article(
                    symbol, title, url, "GNews",
                    pub, item.get("description", ""), agent_source
                ))
        except Exception as e:
            print(f"  ⚠  GNews API error: {e}")
        return articles

    return _cached(cache_key, _fetch)


# ── 4. NewsData.io ────────────────────────────────────────────────────────────

def fetch_newsdata(query: str = "", symbol: str = "", agent_source: str = "API",
                   limit: int = 10) -> list:
    if not NEWSDATA_KEY:
        return []
    cache_key = f"newsdata:{symbol}:{query}"

    def _fetch():
        articles = []
        try:
            q = query or (f"{symbol} stock" if symbol else "stock market India finance")
            params = {
                "apikey":   NEWSDATA_KEY,
                "q":        q,
                "language": "en",
                "category": "business",
            }
            r = requests.get(
                "https://newsdata.io/api/1/news",
                params=params, timeout=10
            )
            if r.status_code != 200:
                print(f"  ⚠  NewsData.io: HTTP {r.status_code}")
                return []

            for item in r.json().get("results", [])[:limit]:
                title = item.get("title", "")
                url   = item.get("link", "")
                if not title or not url:
                    continue
                pub = (item.get("pubDate", "") or "")[:19]
                content = " ".join(item.get("content", None) or
                                   item.get("description", None) or [""])
                articles.append(_make_article(
                    symbol, title, url, "NewsData.io",
                    pub, content, agent_source
                ))
        except Exception as e:
            print(f"  ⚠  NewsData.io error: {e}")
        return articles

    return _cached(cache_key, _fetch)


# ── Combined fetchers ─────────────────────────────────────────────────────────

def fetch_apis_for_symbol(symbol: str, company_name: str = "",
                          agent_source: str = "API") -> list:
    """
    Fetch from all 4 APIs for a specific stock symbol.
    Results are cached — duplicate calls with the same symbol return instantly.
    """
    articles = []
    query = f"{company_name or symbol} stock" if company_name else f"{symbol} stock"

    mx = fetch_marketaux(symbol=symbol, agent_source=agent_source, limit=10)
    articles += mx
    if mx: print(f"  📡 Marketaux/{symbol}: {len(mx)} articles")

    gn = fetch_gnews(query=query, symbol=symbol, agent_source=agent_source, limit=10)
    articles += gn
    if gn: print(f"  📡 GNews/{symbol}: {len(gn)} articles")

    nd = fetch_newsdata(query=query, symbol=symbol, agent_source=agent_source, limit=10)
    articles += nd
    if nd: print(f"  📡 NewsData/{symbol}: {len(nd)} articles")

    ca = fetch_currents(query=query, agent_source=agent_source, limit=5)
    articles += ca
    if ca: print(f"  📡 Currents/{symbol}: {len(ca)} articles")

    return articles


def fetch_all_apis(query: str, agent_source: str = "API") -> list:
    """
    Fetch from all 4 APIs for a general query.
    CACHED — if 8 agents call this with the same query, only 1 real HTTP call
    is made. All subsequent calls return the cached result instantly,
    preventing daily quota exhaustion.
    """
    articles = []

    mx = fetch_marketaux(query=query, agent_source=agent_source, limit=10)
    articles += mx

    gn = fetch_gnews(query=query, agent_source=agent_source, limit=10)
    articles += gn

    nd = fetch_newsdata(query=query, agent_source=agent_source, limit=10)
    articles += nd

    ca = fetch_currents(query=query, agent_source=agent_source, limit=10)
    articles += ca

    seen = set()
    deduped = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            deduped.append(a)

    return deduped


def api_status() -> dict:
    return {
        "Marketaux":   "✅" if MARKETAUX_KEY else "❌ missing MARKETAUX_API_KEY",
        "Currents":    "✅" if CURRENTS_KEY  else "❌ missing CURRENTS_API_KEY",
        "GNews":       "✅" if GNEWS_KEY     else "❌ missing GNEWS_API_KEY",
        "NewsData.io": "✅" if NEWSDATA_KEY  else "❌ missing NEWSDATA_API_KEY",
    }


if __name__ == "__main__":
    print("🔑 API Key Status:")
    for name, status in api_status().items():
        print(f"  {name}: {status}")