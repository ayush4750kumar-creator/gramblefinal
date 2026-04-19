"""
agentE.py — Political Leaders & Global Announcements
Sources: Reuters World, AP News, BBC Business/World, PIB India, ANI, RBI press releases
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, is_after_hours, HEADERS, is_financial
from db_utils import save_articles
from datetime import datetime
import requests

SOURCES = [
    # Global news
    ("Reuters World",      "https://feeds.reuters.com/reuters/worldNews",      "Reuters"),
    ("Reuters Economy",    "https://feeds.reuters.com/reuters/economyNews",     "Reuters"),
    ("AP Business",        "https://feeds.apnews.com/rss/business",             "AP News"),
    ("AP World",           "https://feeds.apnews.com/rss/world",                "AP News"),
    ("BBC Business",       "http://feeds.bbci.co.uk/news/business/rss.xml",     "BBC News"),
    ("BBC World",          "http://feeds.bbci.co.uk/news/world/rss.xml",        "BBC News"),
    ("Guardian Business",  "https://www.theguardian.com/us/business/rss",       "The Guardian"),
    ("Al Jazeera Economy", "https://www.aljazeera.com/xml/rss/all.xml",         "Al Jazeera"),
    # India official
    ("PIB India",          "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", "PIB (Govt of India)"),
    ("PIB Finance",        "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1",    "PIB Finance"),
    ("ANI News",           "https://www.aninews.in/rss/business.xml",           "ANI"),
    ("NDTV India",         "https://feeds.feedburner.com/ndtvnews-india-news",  "NDTV"),
]

# Keywords that make an article "political / global announcement"
GLOBAL_KEYWORDS = [
    "rbi", "sebi", "niti aayog", "finance minister", "nirmala sitharaman",
    "prime minister", "president", "white house", "federal reserve", "fed ",
    "rate cut", "rate hike", "interest rate", "inflation", "gdp", "cpi", "wpi",
    "budget", "policy", "tax", "tariff", "sanction", "g20", "g7", "imf", "world bank",
    "trade war", "trade deal", "geopolit", "oil price", "opec", "crude",
    "ukraine", "china", "trump", "biden", "modi", "central bank",
    "election", "vote", "parliament", "congress", "senate",
]

def is_global_announcement(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in GLOBAL_KEYWORDS)

def fetch_rbi_releases() -> list:
    """RBI press releases RSS."""
    articles = []
    try:
        url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
        rss_url = "https://www.rbi.org.in/scripts/rss.aspx?Id=4"
        entries = fetch_rss(rss_url, "RBI Press Releases", timeout=8)
        for e in entries[:20]:
            link = e.get('link', '')
            title = e.get('title', '')
            pub = parse_date(e)
            articles.append({
                'symbol':          '',
                'title':           f"[RBI] {title}",
                'url':             link,
                'source':          'RBI India',
                'tag_source_name': 'Reserve Bank of India (Official)',
                'published_at':    pub,
                'full_text':       clean_html(e.get('summary', '')),
                'tag_feed':        'global',
                'tag_category':    'official',
                'agent_source':    'E',
                'tag_after_hours': is_after_hours(pub),
            })
    except Exception as e:
        print(f"  ⚠  RBI: {e}")
    return articles

def run() -> int:
    print("🌍 AgentE — Political & Global Announcements")
    articles = []
    seen_urls = set()
    live_feeds = 0

    for source_name, url, display_name in SOURCES:
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
            # AgentE focuses on political / macro articles
            if not is_global_announcement(combined) and source_name not in ('PIB India', 'PIB Finance', 'ANI News'):
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
                'tag_feed':        'global',
                'tag_category':    'official',
                'agent_source':    'E',
                'tag_after_hours': is_after_hours(pub),
            })

    print(f"  📡 RSS: {live_feeds}/{len(SOURCES)} live, {len(articles)} articles")

    for q in ["RBI monetary policy rate decision", "Federal Reserve interest rate decision", "India budget tax policy economy", "global trade tariff oil price"]:
        gnews = fetch_google_news(q, "E", "official")
        for a in gnews:
            if is_global_announcement(a["title"] + " " + a["full_text"]):
                articles.append(a)
    rbi = fetch_rbi_releases()
    articles += rbi
    print(f"  📡 RBI: {len(rbi)} releases")

    saved = save_articles(articles)
    print(f"  ✅ AgentE done — {len(articles)} total, {saved} new saved\n")
    return saved

if __name__ == '__main__':
    run()
