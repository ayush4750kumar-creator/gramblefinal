"""
agentF.py — Official Exchange & Market News
Sources: WSJ, FT, MarketWatch, NASDAQ, NSE Press, SEBI + 4 News APIs
"""
from agentB import fetch_google_news
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, is_recent, HEADERS, BSE_HEADERS, nse_session, bse_session, safe_json, is_financial
from db_utils import save_articles
from news_apis import fetch_all_apis
from datetime import datetime, timedelta
import requests, time

SOURCES = [
    ("WSJ Markets",         "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",          "Wall Street Journal"),
    ("WSJ Economy",         "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",        "Wall Street Journal"),
    ("Financial Times",     "https://www.ft.com/rss/home",                             "Financial Times"),
    ("MarketWatch",         "https://feeds.marketwatch.com/marketwatch/topstories/",   "MarketWatch"),
    ("MarketWatch Markets", "https://feeds.marketwatch.com/marketwatch/marketpulse/",  "MarketWatch"),
    ("Nasdaq News",         "https://www.nasdaq.com/feed/rssoutbound?category=Markets","NASDAQ"),
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

def fetch_nse_press_releases():
    articles = []
    try:
        # Use shared nse_session() — plain requests without cookies returns empty body
        session = nse_session()
        url  = "https://www.nseindia.com/api/press-releases?index=equities"
        resp = session.get(url, timeout=10)
        data = safe_json(resp, "NSE press")
        if not data:
            return articles
        for item in (data if isinstance(data, list) else [])[:30]:
            title = item.get('title','') or item.get('subject','')
            link  = item.get('link','') or "https://www.nseindia.com/press-releases"
            pub   = str(item.get('date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))[:19]
            sym   = extract_symbol(title)
            articles.append({
                'symbol': sym,'title': f"[NSE Press] {title}",'url': link,
                'source': 'NSE Press Release','tag_source_name': 'NSE India (Press)',
                'published_at': pub,'full_text': title,
                'tag_feed': detect_feed(sym, title),'tag_category': 'official',
                'agent_source': 'F','tag_after_hours': is_after_hours(pub),
            })
    except Exception as e:
        print(f"  ⚠  NSE press: {e}")
    return articles

def fetch_sebi_orders():
    """
    SEBI removed their old RSS feed at /sebi_data/attachdocs/rss.xml (404).
    We now use their JSON circulars API instead.
    Falls back to scraping the HTML press release list if the API also fails.
    """
    articles = []

    # ── Primary: SEBI circulars JSON API ─────────────────────────────────────
    try:
        url  = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doLatestNews=yes&type=1&lang=en"
        resp = requests.get(url, headers={**HEADERS, "Referer": "https://www.sebi.gov.in/"}, timeout=10)
        data = safe_json(resp, "SEBI circulars API")
        items = []
        if data:
            # Response is either a list or {"data": [...]}
            items = data if isinstance(data, list) else data.get("data", data.get("Table", []))

        for item in items[:15]:
            title = item.get("heading", "") or item.get("HEADING", "") or item.get("title", "")
            link  = item.get("link", "") or item.get("LINK", "")
            if not link.startswith("http"):
                link = "https://www.sebi.gov.in" + link
            pub   = str(item.get("date", item.get("DATE", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))))[:19]
            sym   = extract_symbol(title)
            articles.append({
                'symbol': sym, 'title': f"[SEBI] {title}", 'url': link,
                'source': 'SEBI', 'tag_source_name': 'SEBI (Official)',
                'published_at': pub, 'full_text': title,
                'tag_feed': detect_feed(sym, title), 'tag_category': 'official',
                'agent_source': 'F', 'tag_after_hours': is_after_hours(pub),
            })
        if articles:
            return articles
    except Exception as e:
        print(f"  ⚠  SEBI circulars API: {e}")

    # ── Fallback: SEBI press release RSS (different path, still live) ─────────
    try:
        fallback_urls = [
            "https://www.sebi.gov.in/sebi_data/attachdocs/press-release-rss.xml",
            "https://www.sebi.gov.in/rss/latestnews.xml",
        ]
        for rss_url in fallback_urls:
            entries = fetch_rss(rss_url, "SEBI RSS fallback", timeout=8)
            if entries:
                for e in entries[:15]:
                    link  = e.get('link', '')
                    title = e.get('title', '')
                    pub   = parse_date(e)
                    sym   = extract_symbol(title)
                    articles.append({
                        'symbol': sym, 'title': f"[SEBI] {title}", 'url': link,
                        'source': 'SEBI', 'tag_source_name': 'SEBI (Official)',
                        'published_at': pub, 'full_text': clean_html(e.get('summary', '')),
                        'tag_feed': detect_feed(sym, title), 'tag_category': 'official',
                        'agent_source': 'F', 'tag_after_hours': is_after_hours(pub),
                    })
                return articles
    except Exception as e:
        print(f"  ⚠  SEBI RSS fallback: {e}")

    # ── Last resort: Google News for SEBI orders ──────────────────────────────
    try:
        import urllib.parse
        q   = urllib.parse.quote("SEBI order circular penalty India")
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        entries = fetch_rss(url, "SEBI via Google News", timeout=8)
        for e in entries[:10]:
            link  = e.get('link', '')
            title = e.get('title', '')
            if 'sebi' not in title.lower():
                continue
            pub = parse_date(e)
            sym = extract_symbol(title)
            articles.append({
                'symbol': sym, 'title': f"[SEBI] {title}", 'url': link,
                'source': 'SEBI (via Google News)', 'tag_source_name': 'SEBI (Official)',
                'published_at': pub, 'full_text': clean_html(e.get('summary', '')),
                'tag_feed': detect_feed(sym, title), 'tag_category': 'official',
                'agent_source': 'F', 'tag_after_hours': is_after_hours(pub),
            })
    except Exception as e:
        print(f"  ⚠  SEBI Google News fallback: {e}")

    return articles

def run() -> int:
    print("🏛️  AgentF — Official Exchange & Market News")
    articles  = []
    seen_urls = set()
    live_feeds  = 0
    skipped_old = 0

    for source_name, url, display_name in SOURCES:
        entries = fetch_rss(url, source_name)
        if entries: live_feeds += 1
        for e in entries:
            link = e.get('link','')
            if not link or link in seen_urls: continue
            pub = parse_date(e)
            if not is_recent(pub):
                skipped_old += 1
                continue
            seen_urls.add(link)
            title   = e.get('title','')
            summary = clean_html(e.get('summary','') or e.get('description',''))
            symbol  = extract_symbol(title + ' ' + summary)
            articles.append({
                'symbol': symbol,'title': title,'url': link,
                'source': source_name,'tag_source_name': display_name,
                'published_at': pub,'full_text': summary,
                'tag_feed': detect_feed(symbol, title),'tag_category': 'news',
                'agent_source': 'F','tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {live_feeds}/{len(SOURCES)} live, {len(articles)} recent articles ({skipped_old} skipped)")

    nse  = fetch_nse_press_releases()
    sebi = fetch_sebi_orders()
    articles += nse + sebi
    print(f"  📡 NSE Press: {len(nse)} | SEBI: {len(sebi)} (no time filter)")

    # ── 4 News APIs ───────────────────────────────────────────────────────────
    api_arts = fetch_all_apis("NASDAQ NYSE Wall Street stock market exchange finance", agent_source="F")
    new_api  = [a for a in api_arts if a["url"] not in seen_urls]
    for a in new_api:
        seen_urls.add(a["url"])
    articles += new_api
    print(f"  📡 News APIs: {len(new_api)} additional articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentF done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()