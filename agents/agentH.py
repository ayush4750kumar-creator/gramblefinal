"""
agentH.py — Top Company News Fetcher (Parallel)
Fetches news for top 50 Indian + top 50 US companies using Google News RSS
Runs all companies in parallel with ThreadPoolExecutor
"""
import sys, os, urllib.parse, time
sys.path.insert(0, os.path.dirname(__file__))
from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, HEADERS
from db_utils import save_articles
from concurrent.futures import ThreadPoolExecutor, as_completed

TOP_INDIA = [
    ("RELIANCE", "Reliance Industries"),
    ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("ICICIBANK", "ICICI Bank"),
    ("INFOSYS", "Infosys"),
    ("SBIN", "State Bank of India"),
    ("BAJFINANCE", "Bajaj Finance"),
    ("HINDUNILVR", "Hindustan Unilever"),
    ("ITC", "ITC Limited"),
    ("LT", "Larsen Toubro"),
    ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("AXISBANK", "Axis Bank"),
    ("WIPRO", "Wipro"),
    ("HCLTECH", "HCL Technologies"),
    ("ASIANPAINT", "Asian Paints"),
    ("MARUTI", "Maruti Suzuki"),
    ("TATAMOTORS", "Tata Motors"),
    ("TATASTEEL", "Tata Steel"),
    ("NTPC", "NTPC"),
    ("POWERGRID", "Power Grid"),
    ("ONGC", "ONGC"),
    ("SUNPHARMA", "Sun Pharma"),
    ("DRREDDY", "Dr Reddy's"),
    ("CIPLA", "Cipla"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("ADANIENT", "Adani Enterprises"),
    ("ADANIPORTS", "Adani Ports"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("JSWSTEEL", "JSW Steel"),
    ("HINDALCO", "Hindalco"),
    ("TECHM", "Tech Mahindra"),
    ("LTIM", "LTIMindtree"),
    ("TITAN", "Titan Company"),
    ("NESTLEIND", "Nestle India"),
    ("ZOMATO", "Zomato"),
    ("PAYTM", "Paytm"),
]

TOP_US = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("NVDA", "Nvidia"),
    ("GOOGL", "Google Alphabet"),
    ("AMZN", "Amazon"),
    ("META", "Meta Facebook"),
    ("TSLA", "Tesla"),
    ("JPM", "JPMorgan Chase"),
    ("V", "Visa"),
    ("BAC", "Bank of America"),
    ("NFLX", "Netflix"),
    ("AMD", "AMD"),
    ("INTC", "Intel"),
    ("ORCL", "Oracle"),
    ("WMT", "Walmart"),
    ("DIS", "Disney"),
    ("GS", "Goldman Sachs"),
    ("MS", "Morgan Stanley"),
    ("PYPL", "PayPal"),
    ("UBER", "Uber"),
    ("COIN", "Coinbase"),
    ("PLTR", "Palantir"),
]

def fetch_company_news(symbol: str, name: str) -> list:
    articles = []
    try:
        query = f"{name} stock earnings results"
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        entries = fetch_rss(url, f"{symbol}", timeout=5)
        for e in entries[:3]:
            link = e.get('link', '')
            title = e.get('title', '')
            if not link or not title:
                continue
            pub = parse_date(e)
            detected = extract_symbol(title) or symbol
            articles.append({
                'symbol':          detected,
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

def run() -> int:
    print("📰 AgentH — Top Company News (Parallel)")
    all_companies = TOP_INDIA + TOP_US
    articles = []
    seen_urls = set()

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_company_news, sym, name): sym
                   for sym, name in all_companies}
        for fut in as_completed(futures, timeout=45):
            try:
                for a in fut.result():
                    if a['url'] not in seen_urls:
                        seen_urls.add(a['url'])
                        articles.append(a)
            except Exception:
                pass

    print(f"  📡 Fetched {len(articles)} articles from {len(all_companies)} companies")
    saved = save_articles(articles)
    print(f"  ✅ AgentH done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
