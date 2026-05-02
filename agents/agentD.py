"""
agentD.py — Official Company Statements
Sources: BSE/NSE/SEC filings + 4 News APIs
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, HEADERS, BSE_HEADERS, nse_session, bse_session, safe_json, COMPANY_MAP
from db_utils import save_articles
from news_apis import fetch_all_apis
from datetime import datetime, timedelta
import requests, time

SEC_TICKERS = {
    "AAPL":  "0000320193",
    "MSFT":  "0000789019",
    "GOOGL": "0001652044",
    "META":  "0001326801",
    "AMZN":  "0001018724",
    "NVDA":  "0001045810",
    "TSLA":  "0001318605",
}

BSE_CATEGORIES = [
    ("Results",       "Result"),
    ("Dividends",     "Dividend"),
    ("Board Meeting", "BoardMeeting"),
    ("Buyback",       "Buyback"),
    ("Amalgamation",  "Amalgamation"),
]

def fetch_sec_edgar(symbol, cik):
    articles = []
    try:
        rss_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcompany&CIK={cik}&type=8-K"
            f"&dateb=&owner=include&count=5&search_text=&output=atom"
        )
        entries = fetch_rss(rss_url, f"SEC/{symbol}", timeout=10)
        for e in entries[:5]:
            link  = e.get('link','')
            title = e.get('title','')
            pub   = parse_date(e)
            if not link or not title: continue
            articles.append({
                'symbol': symbol,'title': f"[SEC 8-K] {symbol}: {title}",
                'url': link,'source': 'SEC Edgar',
                'tag_source_name': 'SEC Edgar (Official)',
                'published_at': pub,'full_text': clean_html(e.get('summary','')),
                'tag_feed': 'company','tag_category': 'official',
                'agent_source': 'D','tag_after_hours': 0,
            })
    except Exception as e:
        print(f"  ⚠  SEC Edgar {symbol}: {e}")
    return articles

def fetch_bse_category(cat_name, cat_code):
    articles = []
    try:
        today    = datetime.utcnow().strftime('%Y%m%d')
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y%m%d')
        url = (
            f"https://api.bseindia.com/BseIndiaAPI/api/AnnGetAnnouncementList/w"
            f"?strCat={cat_code}&strPrevDate={week_ago}&strScrip=&strSearch=P"
            f"&strToDate={today}&strType=C&subcategory=-1"
        )
        # bse_session() warms up cookies — plain requests returns HTML auth wall
        session = bse_session()
        resp = session.get(url, headers=BSE_HEADERS, timeout=8)
        data = safe_json(resp, f"BSE {cat_name}")
        if not data:
            return articles
        for item in (data.get('Table', []) or [])[:20]:
            sym_name = item.get('SLONGNAME','')
            title    = item.get('HEADLINE','')
            sym      = extract_symbol(sym_name + ' ' + title)
            attach   = item.get('ATTACHMENTNAME','')
            link = (
                f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attach}"
                if attach else
                f"https://www.bseindia.com/corporates/ann.html#{sym}"
            )
            pub = str(item.get('NEWS_DT', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))[:19]
            articles.append({
                'symbol': sym or item.get('SCRIP_CD',''),
                'title': f"[BSE {cat_name}] {sym_name}: {title}",
                'url': link,'source': f'BSE {cat_name}',
                'tag_source_name': 'BSE India (Official)',
                'published_at': pub,'full_text': title,
                'tag_feed': 'company','tag_category': 'official',
                'agent_source': 'D','tag_after_hours': 0,
            })
    except Exception as e:
        print(f"  ⚠  BSE {cat_name}: {e}")
    return articles

def fetch_nse_filings():
    articles = []
    try:
        # nse_session() handles the cookie warmup that NSE requires
        session = nse_session()
        url  = "https://www.nseindia.com/api/corporate-announcements?index=equities&from_date=&to_date=&csv=false"
        resp = session.get(url, timeout=10)
        data = safe_json(resp, "NSE filings")
        if not data:
            return articles
        for item in (data if isinstance(data, list) else [])[:60]:
            sym   = item.get('symbol','')
            title = item.get('subject','') or item.get('desc','')
            link  = (
                f"https://nsearchives.nseindia.com/corporate/{item.get('attchmntFile','')}"
                if item.get('attchmntFile')
                else "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
            )
            pub = item.get('an_dt', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            articles.append({
                'symbol': sym,'title': f"[NSE Official] {sym}: {title}",
                'url': link + f"?t={int(time.time())}",
                'source': 'NSE Corporate','tag_source_name': 'NSE India (Official)',
                'published_at': str(pub)[:19],'full_text': title,
                'tag_feed': 'company','tag_category': 'official',
                'agent_source': 'D','tag_after_hours': 0,
            })
    except Exception as e:
        print(f"  ⚠  NSE filings: {e}")
    return articles

def run() -> int:
    print("📋 AgentD — Official Company Statements (no time filter)")
    articles = []

    for cat_name, cat_code in BSE_CATEGORIES:
        batch = fetch_bse_category(cat_name, cat_code)
        articles += batch
        print(f"  📋 BSE {cat_name}: {len(batch)}")

    nse = fetch_nse_filings()
    articles += nse
    print(f"  📋 NSE filings: {len(nse)}")

    for symbol, cik in SEC_TICKERS.items():
        batch = fetch_sec_edgar(symbol, cik)
        articles += batch
        time.sleep(0.3)
    print(f"  📋 SEC Edgar: fetched for {len(SEC_TICKERS)} companies")

    # ── 4 News APIs ───────────────────────────────────────────────────────────
    seen = {a["url"] for a in articles}
    api_arts = fetch_all_apis("BSE NSE official filing earnings dividend results India", agent_source="D")
    new_api  = [a for a in api_arts if a["url"] not in seen]
    articles += new_api
    print(f"  📡 News APIs: {len(new_api)} additional articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentD done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()