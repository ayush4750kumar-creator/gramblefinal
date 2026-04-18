"""
agentSearch.py — Search Agent
When a user searches for a stock/topic, this agent:
  1. Fetches fresh news for that query from RSS + Yahoo Finance
  2. Saves articles through the normal ingest pipeline
  3. Returns article IDs so the frontend can show them immediately

Called via: POST /api/news/search-agent  { query, symbol }
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from fetch_utils import fetch_rss, parse_date, clean_html, extract_symbol, HEADERS, COMPANY_MAP
from db_utils import save_articles
import requests

SEARCH_SOURCES = [
    ("MoneyControl", "https://www.moneycontrol.com/rss/latestnews.xml"),
    ("ET Markets",   "https://economictimes.indiatimes.com/markets/rssfeeds/1977021502.cms"),
    ("LiveMint",     "https://www.livemint.com/rss/markets"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Reuters Business",  "https://feeds.reuters.com/reuters/businessNews"),
]

def search_yahoo_rss(query: str, symbol: str = "") -> list:
    """Search Yahoo Finance RSS for a symbol or query."""
    articles = []
    tickers = []

    # If symbol given, use it directly
    if symbol:
        sym_clean = symbol.replace(".NS","").replace(".BO","").upper()
        tickers.append((sym_clean, sym_clean + ".NS"))
        tickers.append((sym_clean, sym_clean))

    # Also try to find symbol from query
    found_sym = extract_symbol(query)
    if found_sym and found_sym not in [t[0] for t in tickers]:
        tickers.append((found_sym, found_sym + ".NS"))

    for sym, ticker in tickers[:3]:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        entries = fetch_rss(url, f"Yahoo/{sym}", timeout=8)
        for e in entries[:15]:
            pub = parse_date(e)
            articles.append({
                "symbol":          sym,
                "title":           e.get("title", ""),
                "url":             e.get("link", ""),
                "source":          "Yahoo Finance",
                "tag_source_name": "Yahoo Finance",
                "published_at":    pub,
                "full_text":       clean_html(e.get("summary", "")),
                "tag_feed":        "company",
                "tag_category":    "news",
                "agent_source":    "SEARCH",
            })
        time.sleep(0.2)

    return articles


def search_rss_feeds(query: str, symbol: str = "") -> list:
    """Search all RSS feeds for articles matching the query."""
    query_lower   = query.lower()
    query_words   = [w for w in query_lower.split() if len(w) > 2]
    symbol_lower  = symbol.lower() if symbol else ""
    articles      = []
    seen_urls     = set()

    # Also find company name variants for matching
    sym_up = (symbol or extract_symbol(query) or "").upper().replace(".NS","").replace(".BO","")
    variants = COMPANY_MAP.get(sym_up, [])

    for source_name, url in SEARCH_SOURCES:
        entries = fetch_rss(url, source_name, timeout=8)
        for e in entries:
            link = e.get("link", "")
            if not link or link in seen_urls:
                continue
            title   = e.get("title", "")
            summary = clean_html(e.get("summary","") or e.get("description",""))
            combined = (title + " " + summary).lower()

            # Match: symbol OR company variants OR any query words
            matched = (
                (symbol_lower and symbol_lower in combined) or
                any(v in combined for v in variants) or
                sum(1 for w in query_words if w in combined) >= max(1, len(query_words) // 2)
            )
            if not matched:
                continue

            seen_urls.add(link)
            detected_sym = extract_symbol(title + " " + summary) or sym_up or None
            pub = parse_date(e)
            articles.append({
                "symbol":          detected_sym,
                "title":           title,
                "url":             link,
                "source":          source_name,
                "tag_source_name": source_name,
                "published_at":    pub,
                "full_text":       summary,
                "tag_feed":        "company" if detected_sym else "global",
                "tag_category":    "news",
                "agent_source":    "SEARCH",
            })

    return articles


def run(query: str, symbol: str = "") -> dict:
    """
    Main entry point.
    Returns { saved, total_found }
    """
    print(f"🔍 AgentSearch — query='{query}' symbol='{symbol}'")

    articles = []

    # 1. Search RSS feeds
    rss_articles = search_rss_feeds(query, symbol)
    articles += rss_articles
    print(f"  📡 RSS matches: {len(rss_articles)}")

    # 2. Yahoo Finance per symbol
    yahoo_articles = search_yahoo_rss(query, symbol)
    articles += yahoo_articles
    print(f"  📡 Yahoo Finance: {len(yahoo_articles)}")

    # 3. Save through normal pipeline (ingest → tag → sentiment → summary)
    saved = save_articles(articles)
    print(f"  ✅ AgentSearch done — {len(articles)} found, {saved} new saved\n")

    return {"saved": saved, "total_found": len(articles)}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--query",  required=True)
    p.add_argument("--symbol", default="")
    args = p.parse_args()
    run(args.query, args.symbol)
