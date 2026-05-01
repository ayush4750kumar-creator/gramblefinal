"""
agentY.py — AI-Powered Tagger (Groq)

Uses Groq LLM to classify every article — no hardcoded company lists.
Assigns:
  • tag_feed        → 'company' | 'global'
  • tag_category    → 'news' | 'opinion' | 'analysis' | 'official' | 'after_hours'
  • tag_after_hours → 0 | 1
  • tag_source_name → clean display name
  • symbol          → stock ticker if company article (e.g. RELIANCE, AAPL)
"""
import sys, os, re, time, json
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_tag, update_article
from fetch_utils import is_after_hours
import requests

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# Load keys same way as agentBacklog/agentGroq
GROQ_KEYS = [k for k in [
    os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(1, 51)
] if k]
if not GROQ_KEYS:
    single = os.environ.get("GROQ_API_KEY", "")
    if single:
        GROQ_KEYS = [single]

_key_available_at = [0.0] * max(len(GROQ_KEYS), 1)
_key_index = 0


def get_best_key() -> tuple:
    now = time.time()
    for i, key in enumerate(GROQ_KEYS):
        if _key_available_at[i] <= now:
            return i, key
    idx  = min(range(len(GROQ_KEYS)), key=lambda i: _key_available_at[i])
    wait = _key_available_at[idx] - now
    time.sleep(wait)
    return idx, GROQ_KEYS[idx]


def mark_key_limited(idx: int, retry_after: float = 60.0):
    earliest = time.time() + retry_after
    if _key_available_at[idx] < earliest:
        _key_available_at[idx] = earliest


def groq_call(prompt: str) -> str:
    if not GROQ_KEYS:
        return ""
    for _ in range(8):
        idx, key = get_best_key()
        try:
            r = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       GROQ_MODEL,
                    "max_tokens":  120,
                    "temperature": 0.0,
                    "messages":    [{"role": "user", "content": prompt}],
                },
                timeout=15,
            )
            if r.status_code == 429:
                retry_after = float(r.headers.get("retry-after", 60))
                mark_key_limited(idx, retry_after)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            continue
        except Exception:
            continue
    return ""


# ── Source name normalisation ─────────────────────────────────────────────────

SOURCE_DISPLAY = {
    "moneycontrol":        "MoneyControl",
    "economic times":      "Economic Times",
    "et markets":          "Economic Times",
    "livemint":            "LiveMint",
    "mint":                "LiveMint",
    "business standard":   "Business Standard",
    "cnbc":                "CNBC TV18",
    "ndtv":                "NDTV Profit",
    "financial express":   "Financial Express",
    "reuters":             "Reuters",
    "bloomberg":           "Bloomberg",
    "ap news":             "AP News",
    "bbc":                 "BBC News",
    "pib":                 "PIB (Govt of India)",
    "ani":                 "ANI",
    "rbi":                 "Reserve Bank of India",
    "sebi":                "SEBI",
    "nse":                 "NSE India",
    "bse":                 "BSE India",
    "sec edgar":           "SEC Edgar",
    "yahoo finance":       "Yahoo Finance",
    "wall street journal": "Wall Street Journal",
    "wsj":                 "Wall Street Journal",
    "financial times":     "Financial Times",
    "marketwatch":         "MarketWatch",
    "seeking alpha":       "Seeking Alpha",
    "nasdaq":              "NASDAQ",
    "guardian":            "The Guardian",
    "al jazeera":          "Al Jazeera",
    "google news":         "Google News",
    "intraday tracker":    "Live Market Data",
    "market indices":      "Market Indices",
}

def detect_source_display(raw_source: str) -> str:
    s = (raw_source or '').lower()
    for key, display in SOURCE_DISPLAY.items():
        if key in s:
            return display
    return raw_source.title() if raw_source else 'Unknown'


# ── AI classification ─────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are a financial news classifier. Given a news article title (and optional snippet), classify it.

Article title: {title}
Snippet: {snippet}

Respond ONLY with a JSON object, no explanation, no markdown:
{{
  "feed": "company" or "global",
  "category": "news" or "analysis" or "opinion" or "official" or "after_hours",
  "symbol": "TICKER or empty string",
  "company_name": "Full company name or empty string"
}}

Rules:
- feed="company" if the article mentions or is primarily about ANY specific named company, brand, or organisation — even if it also mentions broader market context. When in doubt, prefer "company" over "global".
- feed="global" ONLY for pure macro news with NO specific company mentioned: forex rates, commodity prices, index movements, central bank policy, geopolitical events with no company focus.
- symbol: use the primary stock exchange ticker (e.g. RELIANCE, TCS, AAPL, SAVE). Always try to provide a symbol when feed="company". Leave empty only if you truly cannot identify the company's ticker.
- category="official" for regulatory filings, exchange notices, government press releases
- category="after_hours" for pre-market, post-market, overnight, Gift Nifty wrap articles
- category="analysis" for technical analysis, price targets, forecasts, previews
- category="opinion" for editorials, columns, "should you buy" articles
- category="news" for everything else
- Output ONLY the JSON. Nothing else."""


def classify_article(title: str, snippet: str) -> dict:
    """Call Groq to classify one article. Returns dict with feed/category/symbol."""
    prompt = CLASSIFY_PROMPT.format(
        title=title[:200],
        snippet=snippet[:300] if snippet else ""
    )
    raw = groq_call(prompt)
    if not raw:
        return {}
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            # Validate feed
            if data.get("feed") not in ("company", "global"):
                data["feed"] = "global"
            # Validate category
            if data.get("category") not in ("news", "analysis", "opinion", "official", "after_hours"):
                data["category"] = "news"
            # Clean symbol — uppercase, strip spaces, max 10 chars
            sym = str(data.get("symbol") or "").strip().upper()[:10]
            # Reject generic words that aren't tickers
            if sym in ("", "N/A", "NA", "NONE", "NULL", "UNKNOWN"):
                sym = ""
            data["symbol"] = sym
            return data
    except Exception:
        pass
    return {}


# ── Fallback: keyword-based for when Groq is unavailable ─────────────────────

AFTER_HOURS_KEYWORDS = [
    "after hours", "after market", "pre-market", "pre market",
    "gift nifty", "sgx nifty", "overnight", "morning wrap", "evening wrap",
]
OFFICIAL_KEYWORDS = [
    "press release", "circular", "filing", "regulatory", "agm", "egm",
    "board meeting", "sebi order", "rbi notification", "gazette",
]
ANALYSIS_KEYWORDS = [
    "technical analysis", "price target", "target price", "forecast",
    "preview", "outlook", "upgrade", "downgrade", "rating", "valuation",
    "breakout", "support", "resistance", "bull case", "bear case",
]
OPINION_KEYWORDS = [
    "opinion:", "view:", "commentary:", "should you buy", "should you sell",
    "here's why", "explained:", "decoded:", "i think", "in my view",
]

def fallback_classify(title: str, text: str) -> dict:
    combined = (title + " " + text).lower()
    if any(k in combined for k in AFTER_HOURS_KEYWORDS):
        category = "after_hours"
    elif any(k in combined for k in OFFICIAL_KEYWORDS):
        category = "official"
    elif any(k in combined for k in ANALYSIS_KEYWORDS):
        category = "analysis"
    elif any(k in combined for k in OPINION_KEYWORDS):
        category = "opinion"
    else:
        category = "news"
    return {"feed": "global", "category": category, "symbol": ""}


# ── Main run ──────────────────────────────────────────────────────────────────

def run(limit: int = 500) -> int:
    print("🏷️  AgentY — AI Tagger")

    if not GROQ_KEYS:
        print("  ⚠  No Groq keys found — falling back to keyword tagging")

    articles = get_pending_tag(limit)
    if not articles:
        print("  ℹ  Nothing to tag.\n")
        return 0

    updated   = 0
    ai_tagged = 0
    fb_tagged = 0

    for art in articles:
        title      = art.get('title', '') or ''
        text       = art.get('full_text', '') or ''
        raw_source = art.get('source', '') or ''
        published  = art.get('published_at', '') or ''
        symbol     = art.get('symbol', '') or ''

        # Use snippet: first 300 chars of text or title repeated
        snippet = text[:300] if text else title

        # AI classification
        if GROQ_KEYS:
            result = classify_article(title, snippet)
            time.sleep(0.3)  # ~3 req/s — well under 30 RPM free tier
        else:
            result = {}

        if result:
            ai_tagged += 1
        else:
            result = fallback_classify(title, text)
            fb_tagged += 1

        # Use existing symbol if AI didn't find one
        final_symbol = result.get("symbol") or symbol or ""

        # If AI says company but no symbol, keep feed=company anyway (AI knows best)
        tag_feed        = result.get("feed", "global")
        tag_category    = result.get("category", "news")
        tag_after_hours = is_after_hours(published) if published else 0
        tag_source_name = detect_source_display(raw_source)

        updates = {
            'tag_feed':        tag_feed,
            'tag_category':    tag_category,
            'tag_after_hours': tag_after_hours,
            'tag_source_name': tag_source_name,
        }
        if final_symbol and not art.get('symbol'):
            updates['symbol'] = final_symbol

        update_article(art['id'], updates)
        updated += 1

    print(f"  ✅ AgentY tagged {updated} articles "
          f"(🤖 AI: {ai_tagged} | 🔑 fallback: {fb_tagged})\n")
    return updated


if __name__ == '__main__':
    run()