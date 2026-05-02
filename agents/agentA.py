"""
agentA.py — After-Market Company News
Sources: ET Markets, LiveMint, NDTV Profit, Google News + 4 News APIs
(Yahoo Finance per-stock RSS removed — 429s on every symbol every run)
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, is_recent, COMPANY_MAP, HEADERS, is_financial
from db_utils import save_articles
from news_apis import fetch_all_apis
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

    print(f"  📡 RSS: {len(articles)} recent articles from {live_feeds}/{len(SOURCES)} feeds ({skipped_old} skipped)")

    # ── 4 News APIs (cached — shared across all agents) ───────────────────────
    api_arts = fetch_all_apis("India stock market company earnings results", agent_source="A")
    new_api = [a for a in api_arts if a["url"] not in seen_urls]
    for a in new_api:
        seen_urls.add(a["url"])
        a["tag_after_hours"] = 0
    articles += new_api
    print(f"  📡 News APIs: {len(new_api)} additional articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentA done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()