"""
agentA.py — After-Market Company News
Runs after 15:30 IST. Fetches company-specific news from Indian financial media.
Sources: MoneyControl, Economic Times Markets, LiveMint, Business Standard, Yahoo Finance per-stock
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, is_recent, COMPANY_MAP, HEADERS, is_financial
from db_utils import save_articles
from datetime import datetime
import requests, time

SOURCES = [
    ("ET Markets",       "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms"),
    ("ET Stocks",        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("ET Earnings",      "https://economictimes.indiatimes.com/markets/earnings/rssfeeds/2146842.cms"),
    ("LiveMint Markets", "https://www.livemint.com/rss/markets"),
    ("NDTV Profit",      "https://feeds.feedburner.com/ndtvprofit-latest"),
]

COMPANY_PATTERN = re.compile(
    r'\b[A-Z][a-zA-Z]{1,20}\s+(Ltd|Limited|Inc|Corp|Industries|Enterprises|'
    r'Power|Finance|Bank|Auto|Tech|Pharma|Infra|Energy|Capital|Motors|'
    r'Chemicals|Holdings|Group|Services|Solutions|Ventures|Cement|Steel|'
    r'Telecom|Insurance|Securities|Investments|Retail|Foods|Consumer)\b'
)

def detect_feed(symbol: str, title: str) -> str:
    if symbol and symbol.strip():
        return 'company'
    if title and COMPANY_PATTERN.search(title):
        return 'company'
    return 'company'

def fetch_yahoo_per_stock(symbols: list) -> list:
    articles = []
    for sym in symbols[:5]:
        ticker = sym + ".NS" if not sym.endswith(".NS") and len(sym) <= 10 else sym
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            entries = fetch_rss(url, f"Yahoo/{sym}", timeout=6)
            for e in entries[:10]:
                pub = parse_date(e)
                # ── 1-hour filter ──────────────────────────────────────────
                if not is_recent(pub):
                    continue
                link = e.get('link', '')
                if not link:
                    continue
                articles.append({
                    'symbol':          sym,
                    'title':           e.get('title', ''),
                    'url':             link,
                    'source':          'Yahoo Finance',
                    'tag_source_name': 'Yahoo Finance',
                    'published_at':    pub,
                    'full_text':       clean_html(e.get('summary', '')),
                    'tag_feed':        'company',
                    'tag_category':    'news',
                    'agent_source':    'A',
                    'tag_after_hours': is_after_hours(pub),
                })
            time.sleep(0.1)
        except Exception:
            pass
    return articles

def run() -> int:
    print("📈 AgentA — After-Market Company News")
    articles = []
    seen_urls = set()
    live_feeds = 0
    skipped_old = 0

    for source_name, url in SOURCES:
        entries = fetch_rss(url, source_name)
        if entries:
            live_feeds += 1
        for e in entries:
            link = e.get('link', '')
            if not link or link in seen_urls:
                continue
            pub = parse_date(e)
            # ── 1-hour filter ──────────────────────────────────────────────
            if not is_recent(pub):
                skipped_old += 1
                continue
            seen_urls.add(link)
            title   = e.get('title', '')
            summary = clean_html(e.get('summary', '') or e.get('description', ''))
            symbol  = extract_symbol(title + ' ' + summary)
            articles.append({
                'symbol':          symbol,
                'title':           title,
                'url':             link,
                'source':          source_name,
                'tag_source_name': source_name,
                'published_at':    pub,
                'full_text':       summary,
                'tag_feed':        detect_feed(symbol, title),
                'tag_category':    'news',
                'agent_source':    'A',
                'tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {len(articles)} recent articles from {live_feeds}/{len(SOURCES)} feeds ({skipped_old} skipped — older than 1hr)")

    yahoo_arts = fetch_yahoo_per_stock(list(COMPANY_MAP.keys()))
    articles += yahoo_arts
    print(f"  📡 Yahoo per-stock: {len(yahoo_arts)} recent articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentA done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()