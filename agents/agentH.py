"""
agentH.py — Top Company News Fetcher
Fetches news for top 50 Indian (NSE) + top 50 US (NYSE/NASDAQ) companies
Uses Google News RSS for each company
"""
import sys, os, urllib.parse, time
sys.path.insert(0, os.path.dirname(__file__))
from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, HEADERS
from db_utils import save_articles

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
    ("DIVISLAB", "Divi's Laboratories"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("ADANIENT", "Adani Enterprises"),
    ("ADANIPORTS", "Adani Ports"),
    ("ADANIPOWER", "Adani Power"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("JSWSTEEL", "JSW Steel"),
    ("HINDALCO", "Hindalco"),
    ("TECHM", "Tech Mahindra"),
    ("LTIM", "LTIMindtree"),
    ("HDFCLIFE", "HDFC Life"),
    ("SBILIFE", "SBI Life"),
    ("INDUSINDBK", "IndusInd Bank"),
    ("TITAN", "Titan Company"),
    ("NESTLEIND", "Nestle India"),
    ("BRITANNIA", "Britannia"),
    ("PIDILITIND", "Pidilite Industries"),
    ("HAVELLS", "Havells India"),
    ("BERGEPAINT", "Berger Paints"),
    ("MUTHOOTFIN", "Muthoot Finance"),
    ("CHOLAFIN", "Cholamandalam Finance"),
    ("TRENT", "Trent"),
    ("ZOMATO", "Zomato"),
    ("PAYTM", "Paytm"),
    ("NYKAA", "Nykaa"),
]

TOP_US = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("NVDA", "Nvidia"),
    ("GOOGL", "Google Alphabet"),
    ("AMZN", "Amazon"),
    ("META", "Meta Facebook"),
    ("TSLA", "Tesla"),
    ("AVGO", "Broadcom"),
    ("JPM", "JPMorgan Chase"),
    ("V", "Visa"),
    ("UNH", "UnitedHealth"),
    ("XOM", "ExxonMobil"),
    ("MA", "Mastercard"),
    ("JNJ", "Johnson Johnson"),
    ("PG", "Procter Gamble"),
    ("HD", "Home Depot"),
    ("COST", "Costco"),
    ("BAC", "Bank of America"),
    ("ABBV", "AbbVie"),
    ("CVX", "Chevron"),
    ("MRK", "Merck"),
    ("NFLX", "Netflix"),
    ("AMD", "AMD"),
    ("INTC", "Intel"),
    ("CRM", "Salesforce"),
    ("ORCL", "Oracle"),
    ("ACN", "Accenture"),
    ("TMO", "Thermo Fisher"),
    ("PEP", "PepsiCo"),
    ("KO", "Coca-Cola"),
    ("WMT", "Walmart"),
    ("DIS", "Disney"),
    ("NKE", "Nike"),
    ("MCD", "McDonald's"),
    ("SBUX", "Starbucks"),
    ("GS", "Goldman Sachs"),
    ("MS", "Morgan Stanley"),
    ("BLK", "BlackRock"),
    ("PYPL", "PayPal"),
    ("UBER", "Uber"),
    ("AIRBNB", "Airbnb"),
    ("SNAP", "Snapchat"),
    ("TWTR", "Twitter X"),
    ("SPOT", "Spotify"),
    ("SQ", "Block Square"),
    ("COIN", "Coinbase"),
    ("PLTR", "Palantir"),
    ("RBLX", "Roblox"),
    ("RIVN", "Rivian"),
    ("LCID", "Lucid Motors"),
]

def fetch_company_news(symbol: str, name: str, country: str) -> list:
    """Fetch Google News for a specific company."""
    articles = []
    try:
        query = f"{name} stock earnings results"
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        entries = fetch_rss(url, f"{symbol}", timeout=6)
        for e in entries[:3]:  # max 3 per company
            link = e.get('link', '')
            title = e.get('title', '')
            if not link or not title:
                continue
            pub = parse_date(e)
            articles.append({
                'symbol':          symbol,
                'title':           title,
                'url':             link,
                'source':          'Google News',
                'tag_source_name': f'Google News',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'company',
                'tag_category':    'news',
                'agent_source':    'H',
                'tag_after_hours': 0,
            })
    except Exception as ex:
        pass
    return articles

def run() -> int:
    print("📰 AgentH — Top Company News (India + US)")
    articles = []
    seen_urls = set()

    # Fetch India top 50
    india_count = 0
    for symbol, name in TOP_INDIA:
        news = fetch_company_news(symbol, name, 'IN')
        for a in news:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                articles.append(a)
                india_count += 1
        time.sleep(0.3)  # gentle rate limiting

    print(f"  📡 India top 50: {india_count} articles")

    # Fetch US top 50
    us_count = 0
    for symbol, name in TOP_US:
        news = fetch_company_news(symbol, name, 'US')
        for a in news:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                articles.append(a)
                us_count += 1
        time.sleep(0.3)

    print(f"  📡 US top 50: {us_count} articles")

    saved = save_articles(articles)
    print(f"  ✅ AgentH done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
