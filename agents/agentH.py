"""
agentH.py — Top Company News Fetcher (Parallel)
Sources: Google News + Bing + 4 News APIs
(Yahoo Finance per-stock RSS removed — causes 429 on every run)
"""
import sys, os, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_recent
from db_utils import save_articles
from news_apis import fetch_all_apis
from concurrent.futures import ThreadPoolExecutor, as_completed

TOP_INDIA = [
    ("RELIANCE", "Reliance Industries"),
    ("TCS",      "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"),
    ("INFOSYS",  "Infosys"),
    ("ICICIBANK","ICICI Bank"),
]

TOP_US = [
    ("AAPL",  "Apple"),
    ("MSFT",  "Microsoft"),
    ("NVDA",  "Nvidia"),
    ("GOOGL", "Google Alphabet"),
    ("AMZN",  "Amazon"),
]

GLOBAL_TOPICS = [
    ("MARKET", "Indian stock market Nifty Sensex"),
    ("MARKET", "US stock market S&P 500 Nasdaq"),
    ("CRYPTO", "Bitcoin Ethereum cryptocurrency"),
]

QUERY_TEMPLATES = [
    "{name} NSE share price",
    "{name} news today",
    "{name} stock",
]

def fetch_google_news(symbol, query, lang="en-IN", country="IN"):
    articles = []
    try:
        q   = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang[:2]}"
        entries = fetch_rss(url, symbol, timeout=5)
        for e in entries[:4]:
            link  = e.get('link','')
            title = e.get('title','')
            if not link or not title: continue
            pub = parse_date(e)
            if not is_recent(pub): continue
            detected = extract_symbol(title) or symbol
            articles.append({
                'symbol': detected if detected != symbol else symbol,
                'title': title,'url': link,
                'source': 'Google News','tag_source_name': 'Google News',
                'published_at': pub,'full_text': clean_html(e.get('summary','')),
                'tag_feed': 'company','tag_category': 'news',
                'agent_source': 'H','tag_after_hours': 0,
            })
    except Exception:
        pass
    return articles

def fetch_bing_news(symbol, query):
    articles = []
    try:
        q   = urllib.parse.quote(query)
        url = f"https://www.bing.com/news/search?q={q}&format=rss"
        entries = fetch_rss(url, f"Bing/{symbol}", timeout=5)
        for e in entries[:3]:
            link  = e.get('link','')
            title = e.get('title','')
            if not link or not title: continue
            pub = parse_date(e)
            if not is_recent(pub): continue
            detected = extract_symbol(title) or symbol
            articles.append({
                'symbol': detected,'title': title,'url': link,
                'source': 'Bing News','tag_source_name': 'Bing News',
                'published_at': pub,'full_text': clean_html(e.get('summary','')),
                'tag_feed': 'company','tag_category': 'news',
                'agent_source': 'H','tag_after_hours': 0,
            })
    except Exception:
        pass
    return articles

def fetch_one_company(symbol, name):
    results   = []
    seen_urls = set()

    for template in QUERY_TEMPLATES:
        query = template.format(name=name)
        for a in fetch_google_news(symbol, query):
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                results.append(a)

    # Only use Bing as fallback if Google News returned nothing
    if not results:
        for a in fetch_bing_news(symbol, f"{name} stock news"):
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                results.append(a)

    return results

def fetch_one_topic(symbol, query):
    return fetch_google_news(symbol, query, lang="en-US", country="US")

def run() -> int:
    print("📰 AgentH — Google + Bing + News APIs (Parallel, 6-hour filter)")
    articles  = []
    seen_urls = set()

    all_tasks = (
        [(sym, name, 'company') for sym, name in TOP_INDIA + TOP_US] +
        [(sym, query, 'topic')  for sym, query in GLOBAL_TOPICS]
    )

    with ThreadPoolExecutor(max_workers=6) as ex:
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

    print(f"📡 Fetched {len(articles)} recent articles from Google/Bing")

    # ── News APIs (cached — won't re-hit quota if other agents already called) ─
    for topic_query in [
        "Apple Microsoft Nvidia Google Amazon stock earnings",
        "India Reliance TCS HDFC Infosys stock news today",
        "Bitcoin cryptocurrency market today",
    ]:
        api_arts = fetch_all_apis(topic_query, agent_source="H")
        for a in api_arts:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                articles.append(a)
    print(f"📡 Total after News APIs: {len(articles)} articles")

    saved = save_articles(articles)
    print(f"✅ Saved {saved} new articles\n")
    return saved

if __name__ == "__main__":
    run()