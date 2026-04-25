"""
agentWatchlist.py — Watchlist News Fetcher
Runs after agentX in the pipeline. Fetches news for ALL unique symbols
across ALL users' watchlists.

Can also be triggered for a single symbol:
  python3 agentWatchlist.py --symbol RELIANCE
"""
import sys, os, re, time, argparse
sys.path.insert(0, os.path.dirname(__file__))

import urllib.parse
from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_recent, COMPANY_MAP
from db_utils import save_articles, get_conn

COMPANY_PATTERN = re.compile(
    r'\b[A-Z][a-zA-Z]{1,20}\s+(Ltd|Limited|Inc|Corp|Industries|Enterprises|'
    r'Power|Finance|Bank|Auto|Tech|Pharma|Infra|Energy|Capital|Motors|'
    r'Chemicals|Holdings|Group|Services|Solutions|Ventures|Cement|Steel|'
    r'Telecom|Insurance|Securities|Investments|Retail|Foods|Consumer)\b'
)

SYMBOL_TO_NAME = {
    "RELIANCE":   "Reliance Industries",
    "TCS":        "Tata Consultancy Services TCS",
    "INFY":       "Infosys",
    "HDFCBANK":   "HDFC Bank",
    "ICICIBANK":  "ICICI Bank",
    "WIPRO":      "Wipro",
    "BAJFINANCE": "Bajaj Finance",
    "ADANIENT":   "Adani Enterprises",
    "ADANIPOWER": "Adani Power",
    "ADANIPORTS": "Adani Ports",
    "SBIN":       "State Bank of India SBI",
    "TATAMOTORS": "Tata Motors",
    "MARUTI":     "Maruti Suzuki",
    "SUNPHARMA":  "Sun Pharma",
    "AXISBANK":   "Axis Bank",
    "KOTAKBANK":  "Kotak Mahindra Bank",
    "HINDUNILVR": "Hindustan Unilever HUL",
    "ITC":        "ITC Limited",
    "ONGC":       "ONGC Oil Natural Gas",
    "NTPC":       "NTPC Power",
    "TATASTEEL":  "Tata Steel",
    "JSWSTEEL":   "JSW Steel",
    "TITAN":      "Titan Company",
    "NESTLEIND":  "Nestle India",
    "HCLTECH":    "HCL Technologies",
    "TECHM":      "Tech Mahindra",
    "ULTRACEMCO": "UltraTech Cement",
    "ZOMATO":     "Zomato",
    "PAYTM":      "Paytm One97 Communications",
    "NYKAA":      "Nykaa FSN E-Commerce",
    "INDIGO":     "IndiGo InterGlobe Aviation",
    "IRCTC":      "IRCTC Indian Railway",
    "DRREDDY":    "Dr Reddys Laboratories",
    "CIPLA":      "Cipla pharma",
    "APOLLOHOSP": "Apollo Hospitals",
    "BAJAJFINSV": "Bajaj Finserv",
    "DIVISLAB":   "Divis Laboratories",
    "TATACONSUM": "Tata Consumer Products",
    "COALINDIA":  "Coal India",
    "BPCL":       "Bharat Petroleum BPCL",
    "HEROMOTOCO": "Hero MotoCorp",
    "EICHERMOT":  "Eicher Motors Royal Enfield",
    "GRASIM":     "Grasim Industries",
    "HINDALCO":   "Hindalco Industries",
    "LTIM":       "LTIMindtree",
    "ASIANPAINT": "Asian Paints",
    "PIDILITIND": "Pidilite Industries",
    "AAPL":  "Apple AAPL stock",
    "MSFT":  "Microsoft MSFT stock",
    "NVDA":  "Nvidia NVDA stock",
    "GOOGL": "Google Alphabet GOOGL stock",
    "AMZN":  "Amazon AMZN stock",
    "META":  "Meta Facebook META stock",
    "TSLA":  "Tesla TSLA stock",
    "NFLX":  "Netflix NFLX stock",
    "AMD":   "AMD stock semiconductor",
    "INTC":  "Intel INTC stock",
    "UBER":  "Uber stock",
    "JPM":   "JPMorgan Chase JPM stock",
    "BAC":   "Bank of America BAC stock",
    "GS":    "Goldman Sachs GS stock",
    "COIN":  "Coinbase COIN stock",
    "PLTR":  "Palantir PLTR stock",
    "SHOP":  "Shopify SHOP stock",
}


def get_all_watchlist_symbols() -> list:
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM watchlists ORDER BY symbol")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"  ⚠  Could not fetch watchlist symbols: {e}")
        return []


def fetch_news_for_symbol(symbol: str) -> list:
    articles  = []
    seen_urls = set()
    skipped   = 0

    name  = SYMBOL_TO_NAME.get(symbol, symbol)
    query = f"{name} stock NSE BSE earnings results"

    # Google News
    try:
        q   = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        entries = fetch_rss(url, f"GNews/{symbol}", timeout=6)
        for e in entries[:6]:
            link  = e.get('link', '')
            title = e.get('title', '')
            if not link or not title or link in seen_urls:
                continue
            pub = parse_date(e)
            # ── 1-hour filter ──────────────────────────────────────────────
            if not is_recent(pub):
                skipped += 1
                continue
            seen_urls.add(link)
            articles.append({
                'symbol':          symbol,
                'title':           title,
                'url':             link,
                'source':          'Google News',
                'tag_source_name': 'Google News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'company',
                'tag_category':    'news',
                'agent_source':    'WATCHLIST',
                'tag_after_hours': 0,
            })
    except Exception as ex:
        print(f"  ⚠  GNews {symbol}: {ex}")

    # Bing News as backup
    try:
        q   = urllib.parse.quote(f"{name} stock")
        url = f"https://www.bing.com/news/search?q={q}&format=rss"
        entries = fetch_rss(url, f"Bing/{symbol}", timeout=6)
        for e in entries[:4]:
            link  = e.get('link', '')
            title = e.get('title', '')
            if not link or not title or link in seen_urls:
                continue
            pub = parse_date(e)
            # ── 1-hour filter ──────────────────────────────────────────────
            if not is_recent(pub):
                skipped += 1
                continue
            seen_urls.add(link)
            articles.append({
                'symbol':          symbol,
                'title':           title,
                'url':             link,
                'source':          'Bing News',
                'tag_source_name': 'Bing News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'company',
                'tag_category':    'news',
                'agent_source':    'WATCHLIST',
                'tag_after_hours': 0,
            })
    except Exception:
        pass

    return articles, skipped


def mark_ready(symbol: str):
    """Mark only articles that have a summary as ready."""
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(
            """UPDATE articles
               SET is_ready = true
               WHERE symbol = %s
                 AND is_ready = false
                 AND agent_source = 'WATCHLIST'
                 AND summary_60w IS NOT NULL
                 AND summary_60w != ''""",
            (symbol.upper(),)
        )
        updated = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ Marked {updated} articles ready for {symbol}")
    except Exception as e:
        print(f"  ⚠  Could not mark ready: {e}")


def run(symbol: str = None) -> int:
    if symbol:
        symbols = [symbol.upper()]
        print(f"  📋 Watchlist: fetching for {symbol}")
    else:
        symbols = get_all_watchlist_symbols()
        print(f"  📋 Watchlist: {len(symbols)} symbols — {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    if not symbols:
        print("  ℹ  No watchlist symbols found.")
        return 0

    all_articles = []
    total_skipped = 0

    for sym in symbols:
        arts, skipped = fetch_news_for_symbol(sym)
        all_articles += arts
        total_skipped += skipped
        print(f"  📡 {sym}: {len(arts)} recent articles ({skipped} skipped — older than 1hr)")
        time.sleep(0.3)

    saved = save_articles(all_articles)
    print(f"  ✅ AgentWatchlist done — {len(all_articles)} fetched, {saved} new saved, {total_skipped} skipped old\n")
    return saved


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--symbol', default='', help='Fetch for a specific symbol only')
    args = p.parse_args()
    run(symbol=args.symbol or None)