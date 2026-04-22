"""
agentH.py — Top Company News Fetcher (Parallel)
Fetches news for top Indian + US companies using Google News RSS
Runs all companies in parallel with ThreadPoolExecutor
"""
import sys, os, urllib.parse, time
sys.path.insert(0, os.path.dirname(__file__))
from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, HEADERS
from db_utils import save_articles
from concurrent.futures import ThreadPoolExecutor, as_completed

TOP_INDIA = [
    ("RELIANCE",   "Reliance Industries"),
    ("TCS",        "Tata Consultancy Services"),
    ("HDFCBANK",   "HDFC Bank"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("ICICIBANK",  "ICICI Bank"),
    ("INFOSYS",    "Infosys"),
    ("SBIN",       "State Bank of India"),
    ("BAJFINANCE", "Bajaj Finance"),
    ("HINDUNILVR", "Hindustan Unilever"),
    ("ITC",        "ITC Limited"),
    ("LT",         "Larsen Toubro"),
    ("KOTAKBANK",  "Kotak Mahindra Bank"),
    ("AXISBANK",   "Axis Bank"),
    ("WIPRO",      "Wipro"),
    ("HCLTECH",    "HCL Technologies"),
    ("ASIANPAINT", "Asian Paints"),
    ("MARUTI",     "Maruti Suzuki"),
    ("TATAMOTORS", "Tata Motors"),
    ("TATASTEEL",  "Tata Steel"),
    ("NTPC",       "NTPC"),
    ("POWERGRID",  "Power Grid"),
    ("ONGC",       "ONGC"),
    ("SUNPHARMA",  "Sun Pharma"),
    ("DRREDDY",    "Dr Reddy"),
    ("CIPLA",      "Cipla"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("ADANIENT",   "Adani Enterprises"),
    ("ADANIPORTS", "Adani Ports"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("JSWSTEEL",   "JSW Steel"),
    ("HINDALCO",   "Hindalco"),
    ("TECHM",      "Tech Mahindra"),
    ("LTIM",       "LTIMindtree"),
    ("TITAN",      "Titan Company"),
    ("NESTLEIND",  "Nestle India"),
    ("ZOMATO",     "Zomato"),
    ("PAYTM",      "Paytm"),
    ("NYKAA",      "Nykaa"),
    ("INDIGO",     "IndiGo Airlines"),
    ("IRCTC",      "IRCTC"),
    ("DMART",      "DMart Avenue Supermarts"),
    ("COALINDIA",  "Coal India"),
    ("BPCL",       "Bharat Petroleum"),
    ("GRASIM",     "Grasim Industries"),
    ("EICHERMOT",  "Eicher Motors Royal Enfield"),
    ("HEROMOTOCO", "Hero MotoCorp"),
    ("APOLLOHOSP", "Apollo Hospitals"),
    ("DIVISLAB",   "Divis Laboratories"),
    ("TATACONSUM", "Tata Consumer Products"),
    ("PIDILITIND", "Pidilite Industries"),
]

TOP_US = [
    ("AAPL",   "Apple"),
    ("MSFT",   "Microsoft"),
    ("NVDA",   "Nvidia"),
    ("GOOGL",  "Google Alphabet"),
    ("AMZN",   "Amazon"),
    ("META",   "Meta Facebook"),
    ("TSLA",   "Tesla"),
    ("JPM",    "JPMorgan Chase"),
    ("V",      "Visa"),
    ("BAC",    "Bank of America"),
    ("NFLX",   "Netflix"),
    ("AMD",    "AMD"),
    ("INTC",   "Intel"),
    ("ORCL",   "Oracle"),
    ("WMT",    "Walmart"),
    ("DIS",    "Disney"),
    ("GS",     "Goldman Sachs"),
    ("MS",     "Morgan Stanley"),
    ("PYPL",   "PayPal"),
    ("UBER",   "Uber"),
    ("COIN",   "Coinbase"),
    ("PLTR",   "Palantir"),
    ("AVGO",   "Broadcom"),
    ("CRM",    "Salesforce"),
    ("ADBE",   "Adobe"),
    ("QCOM",   "Qualcomm"),
    ("TXN",    "Texas Instruments"),
    ("SHOP",   "Shopify"),
    ("SQ",     "Block Square"),
    ("SNAP",   "Snapchat"),
    ("SPOT",   "Spotify"),
    ("RIVN",   "Rivian"),
    ("OPENAI", "OpenAI"),
    ("ARM",    "ARM Holdings"),
]

GLOBAL_TOPICS = [
    ("MARKET", "Indian stock market Nifty Sensex"),
    ("MARKET", "US stock market S&P 500 Nasdaq"),
    ("CRYPTO", "Bitcoin Ethereum cryptocurrency"),
    ("GOLD",   "Gold silver commodity prices"),
    ("OIL",    "Crude oil OPEC prices"),
    ("MACRO",  "RBI interest rate inflation India"),
    ("MACRO",  "Federal Reserve interest rate US"),
    ("IPO",    "India IPO listing 2026"),
    ("EARNINGS","India quarterly results earnings 2026"),
    ("FOREX",  "USD INR rupee dollar exchange rate"),
]

# ── Broader queries — not just earnings, catches all news types ───────────────
QUERY_TEMPLATES = [
    "{name} NSE share price",        # price movement news
    "{name} news today",             # general today's news
    "{name} stock",                  # broad stock news
]

def fetch_google_news(symbol: str, query: str, lang: str = "en-IN", country: str = "IN") -> list:
    articles = []
    try:
        q   = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang[:2]}"
        entries = fetch_rss(url, symbol, timeout=3)
        for e in entries[:4]:
            link  = e.get('link', '')
            title = e.get('title', '')
            if not link or not title:
                continue
            pub      = parse_date(e)
            detected = extract_symbol(title) or symbol
            articles.append({
                'symbol':          detected if detected != symbol else symbol,
                'title':           title,
                'url':             link,
                'source':          'Google News',
                'tag_source_name': 'Google News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'company',
                'tag_category':    'news',
                'agent_source':    'H',
                'tag_after_hours': 0,
            })
    except Exception:
        pass
    return articles

def fetch_bing_news(symbol: str, query: str) -> list:
    articles = []
    try:
        q   = urllib.parse.quote(query)
        url = f"https://www.bing.com/news/search?q={q}&format=rss"
        entries = fetch_rss(url, f"Bing/{symbol}", timeout=3)
        for e in entries[:3]:
            link  = e.get('link', '')
            title = e.get('title', '')
            if not link or not title:
                continue
            pub      = parse_date(e)
            detected = extract_symbol(title) or symbol
            articles.append({
                'symbol':          detected,
                'title':           title,
                'url':             link,
                'source':          'Bing News',
                'tag_source_name': 'Bing News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'company',
                'tag_category':    'news',
                'agent_source':    'H',
                'tag_after_hours': 0,
            })
    except Exception:
        pass
    return articles

def fetch_one_company(symbol: str, name: str) -> list:
    """Fetch using multiple broad query templates so we always get fresh news."""
    results  = []
    seen_urls = set()

    for template in QUERY_TEMPLATES:
        query = template.format(name=name)
        for a in fetch_google_news(symbol, query):
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                results.append(a)

    # Bing as backup if Google returned nothing
    if not results:
        for a in fetch_bing_news(symbol, f"{name} stock news"):
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                results.append(a)

    return results

def fetch_one_topic(symbol: str, query: str) -> list:
    return fetch_google_news(symbol, query, lang="en-US", country="US")

def run() -> int:
    print("📰 AgentH — Top Company News (Parallel Google + Bing)")
    articles  = []
    seen_urls = set()

    # ── Fetch ALL companies now, not just [:20] ───────────────────────────────
    all_tasks = (
        [(sym, name, 'company') for sym, name in TOP_INDIA + TOP_US] +
        [(sym, query, 'topic')  for sym, query in GLOBAL_TOPICS]
    )

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {}
        for sym, val, task_type in all_tasks:
            if task_type == 'company':
                futures[ex.submit(fetch_one_company, sym, val)] = sym
            else:
                futures[ex.submit(fetch_one_topic, sym, val)] = sym

        for fut in as_completed(futures, timeout=90):
            try:
                for a in fut.result():
                    if a['url'] not in seen_urls:
                        seen_urls.add(a['url'])
                        articles.append(a)
            except Exception:
                pass

    print(f"  📡 Fetched {len(articles)} articles from {len(all_tasks)} queries")
    saved = save_articles(articles)
    print(f"  ✅ AgentH done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()