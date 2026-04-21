"""
agentY.py — Tagger
Reads all untagged articles from DB and assigns:
  • tag_feed        → 'company' | 'global'
  • tag_category    → 'news' | 'opinion' | 'analysis' | 'official' | 'after_hours'
  • tag_after_hours → 0 | 1
  • tag_source_name → clean display name
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_tag, update_article
from fetch_utils import COMPANY_MAP, is_after_hours

# ── Agents whose output is ALWAYS company-specific ───────────────────────────
COMPANY_AGENTS = {'A', 'C', 'D', 'H'}

# ── Regex: catches "Adani Power", "Trent Ltd", "HDFC Bank", etc. ─────────────
COMPANY_PATTERN = re.compile(
    r'\b[A-Z][a-zA-Z]{1,20}\s+(Ltd|Limited|Inc|Corp|Industries|Enterprises|'
    r'Power|Finance|Bank|Auto|Tech|Pharma|Infra|Energy|Capital|Motors|'
    r'Chemicals|Holdings|Group|Services|Solutions|Ventures|Cement|Steel|'
    r'Telecom|Insurance|Securities|Investments|Retail|Foods|Consumer)\b'
)

# ── Source name normalisation map ─────────────────────────────────────────────
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
    "yfinance":            "Yahoo Finance",
    "wall street journal": "Wall Street Journal",
    "wsj":                 "Wall Street Journal",
    "financial times":     "Financial Times",
    "ft":                  "Financial Times",
    "marketwatch":         "MarketWatch",
    "barron":              "Barron's",
    "seeking alpha":       "Seeking Alpha",
    "nasdaq":              "NASDAQ",
    "investopedia":        "Investopedia",
    "intraday tracker":    "Live Market Data",
    "market indices":      "Market Indices",
    "guardian":            "The Guardian",
    "al jazeera":          "Al Jazeera",
}

# ── Category detection keyword sets ──────────────────────────────────────────
OPINION_KEYWORDS = [
    "opinion:", "view:", "column:", "commentary:", "perspective:", "analysis:",
    "why i think", "i believe", "in my view", "analyst says", "expert says",
    "should you buy", "should you sell", "is it time to", "here's why",
    "this is why", "explained:", "decoded:", "what investors should",
]

ANALYSIS_KEYWORDS = [
    "technical analysis", "chart pattern", "rsi", "macd", "moving average",
    "support level", "resistance level", "fibonacci", "breakout", "breakdown",
    "pivot", "target price", "price target", "valuation", "pe ratio",
    "outlook:", "forecast:", "preview:", "expect", "projection",
    "bull case", "bear case", "upgrade", "downgrade", "rating:",
    "recommendation", "buy rating", "sell rating", "hold rating",
    "quarterly preview", "result preview", "earnings estimate",
]

OFFICIAL_KEYWORDS = [
    "[nse]", "[bse]", "[sebi]", "[rbi]", "[sec", "[pib]", "official",
    "press release", "circular", "notification", "gazette", "order:",
    "filing:", "annual report", "agm", "egm", "boardmeeting",
    "regulatory", "compliance",
]

AFTER_HOURS_KEYWORDS = [
    "after hours", "after market", "after bell", "post market",
    "evening wrap", "morning wrap", "pre-market", "pre market",
    "gift nifty", "sgx nifty", "overnight",
]


def detect_source_display(raw_source: str) -> str:
    s = (raw_source or '').lower()
    for key, display in SOURCE_DISPLAY.items():
        if key in s:
            return display
    return raw_source.title() if raw_source else 'Unknown'


def detect_feed(symbol: str, title: str, text: str,
                agent_source: str = '', existing_feed: str = '') -> str:
    """
    Determine 'company' or 'global'.

    Priority order:
      1. Explicit symbol already attached → company
      2. Agent source is a known company-news agent → company
      3. Existing tag set by the agent (trust it) → use as-is
      4. Company name pattern in title → company
      5. COMPANY_MAP variant match → company
      6. Fallback → global
    """
    # 1. Symbol present
    if symbol and symbol.strip():
        return 'company'

    # 2. Agent source is ground truth
    if agent_source.strip().upper() in COMPANY_AGENTS:
        return 'company'

    # 3. Trust the tag the agent already set
    if existing_feed in ('company', 'global'):
        return existing_feed

    # 4. Regex: catches "Adani Power", "HDFC Bank Ltd", etc.
    if COMPANY_PATTERN.search(title):
        return 'company'

    # 5. COMPANY_MAP keyword scan
    combined = (title + ' ' + text).lower()
    for sym, variants in COMPANY_MAP.items():
        for v in variants:
            if v in combined:
                return 'company'

    return 'global'


def detect_category(title: str, text: str, agent_source: str = '') -> str:
    combined = (title + ' ' + (text or '')).lower()

    if agent_source in ('D', 'E') or any(kw in combined for kw in OFFICIAL_KEYWORDS):
        return 'official'
    if any(kw in combined for kw in AFTER_HOURS_KEYWORDS):
        return 'after_hours'
    if any(kw in combined for kw in OPINION_KEYWORDS):
        return 'opinion'
    if any(kw in combined for kw in ANALYSIS_KEYWORDS):
        return 'analysis'
    return 'news'


def run(limit: int = 500) -> int:
    print("🏷️  AgentY — Tagger")
    articles = get_pending_tag(limit)
    if not articles:
        print("  ℹ  Nothing to tag.\n")
        return 0

    updated = 0
    for art in articles:
        title        = art.get('title', '')
        text         = art.get('full_text', '') or ''
        raw_source   = art.get('source', '')
        symbol       = art.get('symbol', '') or ''
        published    = art.get('published_at', '')
        agent_src    = art.get('agent_source', '') or ''
        existing_feed = art.get('tag_feed', '') or ''

        # Re-derive symbol if blank
        if not symbol:
            from fetch_utils import extract_symbol
            symbol = extract_symbol(title + ' ' + text)

        tag_feed        = detect_feed(symbol, title, text, agent_src, existing_feed)
        tag_category    = detect_category(title, text, agent_src)
        tag_after_hours = is_after_hours(published) if published else 0
        tag_source_name = detect_source_display(raw_source)

        updates = {
            'tag_feed':        tag_feed,
            'tag_category':    tag_category,
            'tag_after_hours': tag_after_hours,
            'tag_source_name': tag_source_name,
        }
        if symbol and not art.get('symbol'):
            updates['symbol'] = symbol

        update_article(art['id'], updates)
        updated += 1

    print(f"  ✅ AgentY tagged {updated} articles\n")
    return updated


if __name__ == '__main__':
    run()