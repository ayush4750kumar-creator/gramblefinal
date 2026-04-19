"""
agentC.py — After-Session Impact News
Identifies after-hours articles that will affect the NEXT trading session.
Sources: NSE announcements, BSE after-hours, MoneyControl evening, Reuters evening
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, HEADERS
from db_utils import save_articles
from datetime import datetime
import requests, json, time

SOURCES = [
    ("MoneyControl Evening",      "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("ET After Hours",            "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("LiveMint Evening",          "https://www.livemint.com/rss/markets"),
    ("Reuters Business Evening",  "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("AP Markets",                "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Bloomberg Markets Alt",     "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("Seeking Alpha",             "https://www.thehindubusinessline.com/markets/?service=rss"),
    ("Business Standard Evening", "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms"),
]

# Keywords that signal next-session impact
IMPACT_KEYWORDS = [
    "after hours", "after market", "earnings", "results", "quarterly",
    "guidance", "forecast", "upgrade", "downgrade", "target price",
    "buyback", "dividend", "split", "merger", "acquisition", "deal",
    "ipo", "listing", "fii", "dii", "block deal", "bulk deal",
    "nse notice", "bse notice", "circuit", "suspended", "delisted",
    "rbi", "sebi", "order", "penalty", "regulatory",
]

def fetch_nse_announcements() -> list:
    """Pull NSE corporate announcements API."""
    articles = []
    try:
        url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
        session = requests.Session()
        session.headers.update(HEADERS)
        # NSE requires a cookie first
        session.get("https://www.nseindia.com", timeout=5)
        resp = session.get(url, timeout=8)
        data = resp.json()
        for item in (data if isinstance(data, list) else [])[:50]:
            sym = item.get('symbol', '')
            title = item.get('desc', '') or item.get('subject', '')
            link = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements"
            pub = item.get('an_dt', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            articles.append({
                'symbol':          sym,
                'title':           f"[NSE] {sym}: {title}",
                'url':             link + f"#{sym}_{int(time.time())}",
                'source':          'NSE Corporate',
                'tag_source_name': 'NSE India',
                'published_at':    str(pub)[:19],
                'full_text':       title,
                'tag_feed':        'company',
                'tag_category':    'official',
                'agent_source':    'C',
                'tag_after_hours': 1,
            })
    except Exception as e:
        print(f"  ⚠  NSE announcements: {e}")
    return articles

def fetch_bse_announcements() -> list:
    """Pull BSE corporate announcements."""
    articles = []
    try:
        today = datetime.utcnow().strftime('%Y%m%d')
        url = (
            f"https://api.bseindia.com/BseIndiaAPI/api/AnnGetAnnouncementList/w"
            f"?strCat=-1&strPrevDate={today}&strScrip=&strSearch=P&strToDate={today}&strType=C&subcategory=-1"
        )
        resp = requests.get(url, headers=HEADERS, timeout=8)
        data = resp.json()
        for item in (data.get('Table', []) or [])[:50]:
            sym_code = item.get('SCRIP_CD', '')
            sym_name = item.get('SLONGNAME', sym_code)
            title = item.get('HEADLINE', '')
            link = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{item.get('ATTACHMENTNAME','')}"
            pub = item.get('NEWS_DT', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            sym = extract_symbol(sym_name + ' ' + title)
            articles.append({
                'symbol':          sym or sym_code,
                'title':           f"[BSE] {sym_name}: {title}",
                'url':             link or f"https://www.bseindia.com/corporates/ann.html#{sym_code}",
                'source':          'BSE Corporate',
                'tag_source_name': 'BSE India',
                'published_at':    str(pub)[:19],
                'full_text':       title,
                'tag_feed':        'company',
                'tag_category':    'official',
                'agent_source':    'C',
                'tag_after_hours': 1,
            })
    except Exception as e:
        print(f"  ⚠  BSE announcements: {e}")
    return articles

def is_impact_article(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in IMPACT_KEYWORDS)



def is_market_news(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ['stock', 'market', 'nifty', 'sensex', 'bse', 'nse', 'share', 'equity', 'trading', 'invest', 'earning', 'profit', 'revenue', 'ipo', 'fund', 'economy', 'gdp', 'inflation', 'rate', 'rbi', 'sebi', 'rupee', 'oil', 'gold', 'crypto', 'nasdaq', 'dow', 'fed', 'tariff', 'trade', 'bank', 'finance', 'fiscal'])

def fetch_google_news(query: str, agent_source: str, category: str = 'news') -> list:
    import urllib.parse
    articles = []
    try:
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        entries = fetch_rss(url, f"Google News ({query})")
        for e in entries[:15]:
            link = e.get('link', '')
            title = e.get('title', '')
            if not link or not title:
                continue
            if not is_market_news(title):
                continue
            pub = parse_date(e)
            articles.append({
                'symbol':          extract_symbol(title),
                'title':           title,
                'url':             link,
                'source':          'Google News',
                'tag_source_name': 'Google News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'global',
                'tag_category':    category,
                'agent_source':    agent_source,
                'tag_after_hours': 0,
            })
    except Exception as ex:
        print(f"  Google News ({query}): {ex}")
    return articles

def run() -> int:
    print("🌙 AgentC — After-Session Impact News")
    articles = []
    seen_urls = set()
    live_feeds = 0

    for source_name, url in SOURCES:
        entries = fetch_rss(url, source_name)
        if entries:
            live_feeds += 1
        for e in entries:
            link = e.get('link', '')
            if not link or link in seen_urls:
                continue
            title = e.get('title', '')
            summary = clean_html(e.get('summary', '') or e.get('description', ''))
            combined = title + ' ' + summary
            if not is_impact_article(combined):
                continue  # AgentC only keeps next-session-relevant articles
            seen_urls.add(link)
            symbol = extract_symbol(combined)
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
                'tag_category':    'after_hours',
                'agent_source':    'C',
                'tag_after_hours': 1,
            })

    print(f"  📡 RSS: {live_feeds}/{len(SOURCES)} live, {len(articles)} impact articles")

    nse = fetch_nse_announcements()
    bse = fetch_bse_announcements()
    articles += nse + bse
    print(f"  📡 NSE: {len(nse)} | BSE: {len(bse)} announcements")

    for q in ["NSE BSE earnings results quarterly", "India stock market after hours results", "Indian company quarterly profit revenue"]:
        articles += fetch_google_news(q, "C", "news")
    saved = save_articles(articles)
    print(f"  ✅ AgentC done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
