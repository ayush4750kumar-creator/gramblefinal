"""
agentB.py — Pre-Market News & Analysis
Runs before 9:15 IST. GIFT Nifty signals, global cues, pre-market wrap.
Sources: MoneyControl pre-market, CNBC TV18, Investing.com, SGX/GIFT Nifty via yfinance
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, HEADERS
from db_utils import save_articles
from datetime import datetime
import requests, time

SOURCES = [
    ("MoneyControl Pre-Market",  "https://www.moneycontrol.com/rss/premarketreports.xml"),
    ("MoneyControl Morning",     "https://www.moneycontrol.com/rss/morning-news.xml"),
    ("CNBC TV18 Markets",        "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/market.xml"),
    ("CNBC TV18 Economy",        "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/economy.xml"),
    ("ET Pre-Open",              "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms"),
    ("Business Standard Morning","https://www.business-standard.com/rss/markets-106.rss"),
    ("Investing.com Asia",       "https://www.investing.com/rss/news_25.rss"),
    ("Investing.com Economy",    "https://www.investing.com/rss/news_14.rss"),
    ("Reuters Business",         "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets",          "https://feeds.reuters.com/reuters/companyNews"),
]


def fetch_google_news(query: str, agent_source: str, category: str = 'news') -> list:
    """Fetch Google News RSS as fallback."""
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
        print(f"  ⚠  Google News ({query}): {ex}")
    return articles

def fetch_gift_nifty():
    """Fetch GIFT Nifty / SGX Nifty as a news signal using yfinance."""
    articles = []
    try:
        import yfinance as yf
        # NIFTY 50 futures proxy
        proxies = {
            "^NSEI":  "Nifty 50",
            "^BSESN": "Sensex",
            "^DJI":   "Dow Jones",
            "^IXIC":  "Nasdaq",
            "^GSPC":  "S&P 500",
            "CL=F":   "Crude Oil",
            "GC=F":   "Gold",
            "USDINR=X": "USD/INR",
        }
        lines = []
        for ticker, name in proxies.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d")
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    last_close = hist['Close'].iloc[-1]
                    chg = ((last_close - prev_close) / prev_close) * 100
                    arrow = "▲" if chg > 0 else "▼"
                    lines.append(f"{arrow} {name}: {last_close:.2f} ({chg:+.2f}%)")
            except Exception:
                pass
        if lines:
            summary = "Pre-market cues: " + " | ".join(lines)
            articles.append({
                'symbol':          '',
                'title':           f"Pre-Market Global Cues — {datetime.utcnow().strftime('%d %b %Y')}",
                'url':             f"https://finance.yahoo.com/premarket?t={int(time.time())}",
                'source':          'Market Indices',
                'tag_source_name': 'Market Indices (Yahoo Finance)',
                'published_at':    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'full_text':       summary,
                'tag_feed':        'global',
                'tag_category':    'analysis',
                'agent_source':    'B',
                'tag_after_hours': 1,
            })
    except ImportError:
        print("  ⚠  yfinance not installed — skipping GIFT Nifty cues")
    except Exception as e:
        print(f"  ⚠  GIFT Nifty: {e}")
    return articles

def run() -> int:
    print("🌅 AgentB — Pre-Market News & Analysis")
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
                'tag_category':    'analysis',
                'agent_source':    'B',
                'tag_after_hours': 1,
            })

    print(f"  📡 RSS: {live_feeds}/{len(SOURCES)} feeds live, {len(articles)} articles")

    for q in ["India stock market pre-market", "Nifty Sensex today", "Indian economy news today"]:
        articles += fetch_google_news(q, "B", "analysis")
    gift = fetch_gift_nifty()
    articles += gift
    if gift:
        print(f"  📡 GIFT/Index cues: {len(gift)} synthetic article(s)")

    saved = save_articles(articles)
    print(f"  ✅ AgentB done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
