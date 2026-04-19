"""
agentG.py — Current Trading Session News
Runs during market hours (9:15–15:30 IST). Live fluctuations, intraday analysis.
Sources: NSE live, yfinance intraday, TradingView-compatible feeds, Tickertape,
         MoneyControl live, ET Markets live
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, HEADERS, COMPANY_MAP
from db_utils import save_articles
from datetime import datetime
import requests, time

LIVE_SOURCES = [
    ("MoneyControl Live",    "https://www.moneycontrol.com/rss/latestnews.xml",      "MoneyControl"),
    ("ET Markets Live",      "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms", "Economic Times"),
    ("CNBC TV18 Live",       "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/market.xml", "CNBC TV18"),
    ("Mint Markets",         "https://www.livemint.com/rss/markets",                 "LiveMint"),
    ("Business Standard Live","https://www.business-standard.com/rss/markets-106.rss","Business Standard"),
    ("StockMarketToday",     "https://stockmarkettodaynews.com/feed/",               "StockMarketToday"),
    ("ValueResearch",        "https://www.valueresearchonline.com/rss/fund-news.xml","Value Research"),
]

# Intraday movement keywords
INTRADAY_KEYWORDS = [
    "surges", "jumps", "falls", "drops", "rises", "rallies", "gains", "loses",
    "52-week", "all time", "high", "low", "circuit", "upper circuit", "lower circuit",
    "today", "intraday", "session", "nse", "bse", "nifty", "sensex",
    "volume", "bulk deal", "block deal", "fii buying", "fii selling",
    "support", "resistance", "breakout", "breakdown", "momentum",
    "q1", "q2", "q3", "q4", "results", "earnings", "profit", "revenue",
]

def fetch_intraday_movers() -> list:
    """Use yfinance to detect big movers and create news-like articles."""
    articles = []
    try:
        import yfinance as yf

        watchlist = {
            "RELIANCE.NS": "RELIANCE", "TCS.NS": "TCS",
            "INFY.NS": "INFY",         "HDFCBANK.NS": "HDFCBANK",
            "SBIN.NS": "SBIN",         "ICICIBANK.NS": "ICICIBANK",
            "BAJFINANCE.NS": "BAJFINANCE", "AXISBANK.NS": "AXISBANK",
            "WIPRO.NS": "WIPRO",       "TATAMOTORS.NS": "TATAMOTORS",
            "AAPL": "AAPL",            "TSLA": "TSLA",
            "NVDA": "NVDA",            "MSFT": "MSFT",
            "GOOGL": "GOOGL",          "META": "META",
            "AMZN": "AMZN",
        }

        movers = []
        for ticker, sym in watchlist.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d", interval="1d")
                if len(hist) >= 2:
                    prev = hist['Close'].iloc[-2]
                    curr = hist['Close'].iloc[-1]
                    vol = hist['Volume'].iloc[-1]
                    chg = ((curr - prev) / prev) * 100
                    if abs(chg) >= 2.0:   # only flag notable moves
                        movers.append((sym, ticker, curr, chg, vol))
            except Exception:
                pass

        for sym, ticker, price, chg, vol in movers:
            direction = "surges" if chg > 0 else "falls"
            arrow = "▲" if chg > 0 else "▼"
            title = f"{arrow} {sym} {direction} {abs(chg):.2f}% to {price:.2f} in today's session"
            body = (
                f"{sym} is {direction} {abs(chg):.2f}% to {price:.2f}. "
                f"Volume: {vol:,.0f}. Change: {chg:+.2f}%."
            )
            pub = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            articles.append({
                'symbol':          sym,
                'title':           title,
                'url':             f"https://finance.yahoo.com/quote/{ticker}?t={int(time.time())}",
                'source':          'Intraday Tracker',
                'tag_source_name': 'yfinance Intraday',
                'published_at':    pub,
                'full_text':       body,
                'tag_feed':        'company',
                'tag_category':    'analysis',
                'agent_source':    'G',
                'tag_after_hours': 0,
            })

    except ImportError:
        print("  ⚠  yfinance not installed — skipping intraday movers")
    except Exception as e:
        print(f"  ⚠  intraday movers: {e}")
    return articles

def is_live_article(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in INTRADAY_KEYWORDS)

def run() -> int:
    print("📊 AgentG — Current Trading Session News")
    articles = []
    seen_urls = set()
    live_feeds = 0

    for source_name, url, display_name in LIVE_SOURCES:
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
            if not is_live_article(combined):
                continue
            seen_urls.add(link)
            symbol = extract_symbol(combined)
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
                'tag_category':    'analysis',
                'agent_source':    'G',
                'tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {live_feeds}/{len(LIVE_SOURCES)} live, {len(articles)} intraday articles")

    for q in ["Nifty Sensex stock market today", "NSE BSE stock surge fall today", "India stocks intraday trading"]:
        gnews = fetch_google_news(q, "G", "analysis")
        for a in gnews:
            if is_live_article(a["title"] + " " + a["full_text"]):
                articles.append(a)
    movers = fetch_intraday_movers()
    articles += movers
    print(f"  📡 Intraday movers: {len(movers)}")

    saved = save_articles(articles)
    print(f"  ✅ AgentG done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
