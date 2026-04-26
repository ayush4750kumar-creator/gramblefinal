"""
agentG.py — Current Trading Session News
Sources: Live RSS feeds + Google News + 4 News APIs
"""
from agentB import fetch_google_news
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, is_recent, HEADERS, is_financial, COMPANY_MAP
from db_utils import save_articles
from news_apis import fetch_all_apis
from datetime import datetime
import requests, time

LIVE_SOURCES = [
    ("ET Markets Live", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms", "Economic Times"),
    ("Mint Markets",    "https://www.livemint.com/rss/markets",                                 "LiveMint"),
    ("StockMarketToday","https://stockmarkettodaynews.com/feed/",                               "StockMarketToday"),
]

INTRADAY_KEYWORDS = [
    "surges","jumps","falls","drops","rises","rallies","gains","loses",
    "52-week","all time","high","low","circuit","upper circuit","lower circuit",
    "today","intraday","session","nse","bse","nifty","sensex",
    "volume","bulk deal","block deal","fii buying","fii selling",
    "support","resistance","breakout","breakdown","momentum",
    "q1","q2","q3","q4","results","earnings","profit","revenue",
]

COMPANY_PATTERN = re.compile(
    r'\b[A-Z][a-zA-Z]{1,20}\s+(Ltd|Limited|Inc|Corp|Industries|Enterprises|'
    r'Power|Finance|Bank|Auto|Tech|Pharma|Infra|Energy|Capital|Motors|'
    r'Chemicals|Holdings|Group|Services|Solutions|Ventures|Cement|Steel|'
    r'Telecom|Insurance|Securities|Investments|Retail|Foods|Consumer)\b'
)

def detect_feed(symbol, title):
    if symbol and symbol.strip(): return 'company'
    if title and COMPANY_PATTERN.search(title): return 'company'
    return 'global'

def is_live_article(text):
    return any(kw in text.lower() for kw in INTRADAY_KEYWORDS)

def run() -> int:
    print("📊 AgentG — Current Trading Session News")
    articles  = []
    seen_urls = set()
    live_feeds  = 0
    skipped_old = 0

    for source_name, url, display_name in LIVE_SOURCES:
        entries = fetch_rss(url, source_name)
        if entries: live_feeds += 1
        for e in entries:
            link = e.get('link','')
            if not link or link in seen_urls: continue
            title   = e.get('title','')
            summary = clean_html(e.get('summary','') or e.get('description',''))
            if not is_live_article(title + ' ' + summary): continue
            pub = parse_date(e)
            if not is_recent(pub):
                skipped_old += 1
                continue
            seen_urls.add(link)
            symbol = extract_symbol(title + ' ' + summary)
            articles.append({
                'symbol': symbol,'title': title,'url': link,
                'source': source_name,'tag_source_name': display_name,
                'published_at': pub,'full_text': summary,
                'tag_feed': detect_feed(symbol, title),'tag_category': 'analysis',
                'agent_source': 'G','tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {live_feeds}/{len(LIVE_SOURCES)} live, {len(articles)} recent intraday articles ({skipped_old} skipped)")

    for q in ["Nifty Sensex intraday surge fall today","NSE BSE stock circuit breaker today","India stocks trading volume today"]:
        gnews = fetch_google_news(q, "G", "analysis")
        for a in gnews:
            if is_live_article(a["title"] + " " + a["full_text"]):
                a['tag_feed'] = detect_feed(a.get('symbol',''), a.get('title',''))
                articles.append(a)

    # ── 4 News APIs ───────────────────────────────────────────────────────────
    api_arts = fetch_all_apis("Nifty Sensex intraday trading session stock market today India", agent_source="G")
    new_api  = [a for a in api_arts if a["url"] not in seen_urls]
    for a in new_api:
        seen_urls.add(a["url"])
        a["tag_category"] = "analysis"
    articles += new_api
    print(f"  📡 News APIs: {len(new_api)} additional articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentG done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()