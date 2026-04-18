"""
agentA.py — After-Market Company News
Runs after 15:30 IST. Fetches company-specific news from Indian financial media.
Sources: MoneyControl, Economic Times Markets, LiveMint, Business Standard, Yahoo Finance per-stock
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, COMPANY_MAP, HEADERS
from db_utils import save_articles
from datetime import datetime
import requests, time

SOURCES = [
    ("MoneyControl Latest",       "https://www.moneycontrol.com/rss/latestnews.xml"),
    ("MoneyControl Markets",      "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("ET Markets",                "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms"),
    ("ET Stocks",                 "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("ET Earnings",               "https://economictimes.indiatimes.com/markets/earnings/rssfeeds/2146842.cms"),
    ("LiveMint Markets",          "https://www.livemint.com/rss/markets"),
    ("Business Standard Markets", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Business Standard Stocks",  "https://www.business-standard.com/rss/storyListing/2.rss"),
    ("Financial Express Markets", "https://www.financialexpress.com/market/feed/"),
    ("NDTV Profit",               "https://feeds.feedburner.com/ndtvprofit-latest"),
]

def fetch_yahoo_per_stock(symbols: list) -> list:
    """Fetch 10 articles per symbol from Yahoo Finance RSS."""
    articles = []
    for sym in symbols[:40]:   # cap to avoid hammering
        # Yahoo Finance RSS uses .NS suffix for NSE stocks
        ticker = sym + ".NS" if not sym.endswith(".NS") and len(sym) <= 6 and not sym.isupper() else sym
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        try:
            entries = fetch_rss(url, f"Yahoo/{sym}", timeout=6)
            for e in entries[:10]:
                pub = parse_date(e)
                articles.append({
                    'symbol':          sym,
                    'title':           e.get('title', ''),
                    'url':             e.get('link', ''),
                    'source':          'Yahoo Finance',
                    'tag_source_name': 'Yahoo Finance',
                    'published_at':    pub,
                    'full_text':       clean_html(e.get('summary', '')),
                    'tag_feed':        'company',
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

    # RSS feeds
    for source_name, url in SOURCES:
        entries = fetch_rss(url, source_name)
        for e in entries:
            link = e.get('link', '')
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)
            title = e.get('title', '')
            summary = clean_html(e.get('summary', '') or e.get('description', ''))
            symbol = extract_symbol(title + ' ' + summary)
            pub = parse_date(e)
            articles.append({
                'symbol':          symbol,
                'title':           title,
                'url':             link,
                'source':          source_name,
                'tag_source_name': source_name,
                'published_at':    pub,
                'full_text':       summary,
                'tag_feed':        'company' if symbol else 'global',
                'agent_source':    'A',
                'tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {len(articles)} articles from {len(SOURCES)} feeds")

    # Yahoo Finance per-stock for top 40 symbols
    yahoo_arts = fetch_yahoo_per_stock(list(COMPANY_MAP.keys()))
    articles += yahoo_arts
    print(f"  📡 Yahoo per-stock: {len(yahoo_arts)} articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentA done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
