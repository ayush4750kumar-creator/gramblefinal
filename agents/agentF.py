from agentB import fetch_google_news
"""
agentF.py — Official Exchange & Market News
Sources: NSE India press, NYSE press, NASDAQ news, Wall Street Journal RSS, Financial Times RSS
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, HEADERS, is_financial
from db_utils import save_articles
from datetime import datetime, timedelta
import requests, time

SOURCES = [
    # Exchange / official market sources
    ("WSJ Markets",        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",     "Wall Street Journal"),
    ("WSJ Economy",        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",   "Wall Street Journal"),
    ("Financial Times",    "https://www.ft.com/rss/home",                        "Financial Times"),
    ("MarketWatch",        "https://feeds.marketwatch.com/marketwatch/topstories/", "MarketWatch"),
    ("MarketWatch Markets","https://feeds.marketwatch.com/marketwatch/marketpulse/","MarketWatch"),
    ("Nasdaq News",        "https://www.nasdaq.com/feed/rssoutbound?category=Markets", "NASDAQ"),
]

def fetch_nse_press_releases() -> list:
    """NSE India press releases."""
    articles = []
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.nseindia.com", timeout=5)
        url = "https://www.nseindia.com/api/press-releases?index=equities"
        resp = session.get(url, timeout=10)
        data = resp.json()
        for item in (data if isinstance(data, list) else [])[:30]:
            title = item.get('title', '') or item.get('subject', '')
            link = item.get('link', '') or "https://www.nseindia.com/press-releases"
            pub = str(item.get('date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))[:19]
            articles.append({
                'symbol':          extract_symbol(title),
                'title':           f"[NSE Press] {title}",
                'url':             link,
                'source':          'NSE Press Release',
                'tag_source_name': 'NSE India (Press)',
                'published_at':    pub,
                'full_text':       title,
                'tag_feed':        'global',
                'tag_category':    'official',
                'agent_source':    'F',
                'tag_after_hours': is_after_hours(pub),
            })
    except Exception as e:
        print(f"  ⚠  NSE press: {e}")
    return articles

def fetch_sebi_orders() -> list:
    """SEBI orders and circulars RSS."""
    articles = []
    try:
        url = "https://www.sebi.gov.in/sebi_data/attachdocs/rss.xml"
        entries = fetch_rss(url, "SEBI", timeout=8)
        for e in entries[:15]:
            link = e.get('link', '')
            title = e.get('title', '')
            pub = parse_date(e)
            articles.append({
                'symbol':          extract_symbol(title),
                'title':           f"[SEBI] {title}",
                'url':             link,
                'source':          'SEBI',
                'tag_source_name': 'SEBI (Official)',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'global',
                'tag_category':    'official',
                'agent_source':    'F',
                'tag_after_hours': is_after_hours(pub),
            })
    except Exception as e:
        print(f"  ⚠  SEBI: {e}")
    return articles

def run() -> int:
    print("🏛️  AgentF — Official Exchange & Market News")
    articles = []
    seen_urls = set()
    live_feeds = 0

    for source_name, url, display_name in SOURCES:
        entries = fetch_rss(url, source_name)
        if entries:
            live_feeds += 1
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
                'tag_source_name': display_name,
                'published_at':    pub,
                'full_text':       summary,
                'tag_feed':        'company' if symbol else 'global',
                'tag_category':    'news',
                'agent_source':    'F',
                'tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {live_feeds}/{len(SOURCES)} live, {len(articles)} articles")

    for q in ["NSE BSE SEBI official circular announcement", "IPO stock market listing today", "NASDAQ NYSE market update"]:
        pass  # fetch_google_news disabled
    nse = fetch_nse_press_releases()
    sebi = fetch_sebi_orders()
    articles += nse + sebi
    print(f"  📡 NSE Press: {len(nse)} | SEBI: {len(sebi)}")

    saved = save_articles(articles)
    print(f"  ✅ AgentF done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
