"""
fetch_utils.py — Shared helpers for RSS parsing, article scraping, and symbol matching.
"""
import feedparser, requests, re, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ── NSE F&O + large-cap symbols with name variants for company matching ──────
COMPANY_MAP = {
    "RELIANCE":    ["reliance", "ril", "mukesh ambani"],
    "TCS":         ["tcs", "tata consultancy"],
    "INFY":        ["infosys", "infy"],
    "HDFCBANK":    ["hdfc bank", "hdfcbank"],
    "ICICIBANK":   ["icici bank"],
    "WIPRO":       ["wipro"],
    "BAJFINANCE":  ["bajaj finance"],
    "ADANIENT":    ["adani enterprises", "adani group"],
    "SBIN":        ["sbi", "state bank"],
    "TATAMOTORS":  ["tata motors"],
    "MARUTI":      ["maruti", "suzuki"],
    "SUNPHARMA":   ["sun pharma", "sun pharmaceutical"],
    "LTIM":        ["ltimindtree", "lti"],
    "AXISBANK":    ["axis bank"],
    "KOTAKBANK":   ["kotak bank", "kotak mahindra"],
    "HINDUNILVR":  ["hindustan unilever", "hul"],
    "ITC":         ["itc limited", "itc ltd"],
    "ONGC":        ["ongc", "oil and natural gas"],
    "NTPC":        ["ntpc"],
    "POWERGRID":   ["power grid", "pgcil"],
    "AAPL":        ["apple", "tim cook"],
    "MSFT":        ["microsoft", "satya nadella"],
    "GOOGL":       ["google", "alphabet", "sundar pichai"],
    "META":        ["meta", "facebook", "mark zuckerberg"],
    "AMZN":        ["amazon", "andy jassy"],
    "NVDA":        ["nvidia", "jensen huang"],
    "TSLA":        ["tesla", "elon musk"],
    "NFLX":        ["netflix"],
    "HDFCLIFE":    ["hdfc life"],
    "BAJAJFINSV":  ["bajaj finserv"],
    "TATASTEEL":   ["tata steel"],
    "JSWSTEEL":    ["jsw steel"],
    "HINDALCO":    ["hindalco"],
    "ULTRACEMCO":  ["ultratech cement"],
    "CIPLA":       ["cipla"],
    "DRREDDY":     ["dr reddy", "dr. reddy"],
    "DIVISLAB":    ["divi's lab", "divis lab"],
    "TECHM":       ["tech mahindra"],
    "HCLTECH":     ["hcl tech", "hcl technologies"],
    "BPCL":        ["bpcl", "bharat petroleum"],
    "COALINDIA":   ["coal india"],
    "EICHERMOT":   ["eicher motors", "royal enfield"],
    "BRITANNIA":   ["britannia"],
    "NESTLEIND":   ["nestle india"],
    "TITAN":       ["titan company"],
    "ASIANPAINT":  ["asian paints"],
    "INDUSINDBK":  ["indusind bank"],
    "GRASIM":      ["grasim"],
    "HEROMOTOCO":  ["hero motocorp"],
    "UPL":         ["upl limited"],
    "SHREECEM":    ["shree cement"],
    "APOLLOHOSP":  ["apollo hospitals"],
    "TATACONSUM":  ["tata consumer"],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def fetch_rss(url: str, source_name: str, timeout=10) -> list:
    """Parse an RSS/Atom feed. Returns list of raw entry dicts."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        return feed.entries
    except Exception as e:
        print(f"  ⚠  RSS {source_name}: {e}")
        return []

def parse_date(entry) -> str:
    """Extract ISO datetime string from feedparser entry."""
    for attr in ('published', 'updated', 'created'):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                return dt.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def clean_html(text: str) -> str:
    """Strip HTML tags."""
    return re.sub(r'<[^>]+>', ' ', text or '').strip()

def extract_symbol(text: str) -> str:
    """Try to match article text to a known company symbol."""
    text_lower = (text or '').lower()
    for symbol, variants in COMPANY_MAP.items():
        for v in variants:
            if v in text_lower:
                return symbol
    return ''

def is_after_hours(dt_str: str) -> int:
    """Return 1 if the article was published outside 9:00–15:30 IST."""
    try:
        dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
        # IST offset = UTC+5:30
        ist_hour = (dt.hour + 5) % 24
        ist_min  = dt.minute + 30
        if ist_min >= 60:
            ist_hour += 1
            ist_min  -= 60
        total = ist_hour * 60 + ist_min
        return 0 if (9 * 60 <= total <= 15 * 60 + 30) else 1
    except Exception:
        return 0

def fetch_article_text(url: str, timeout=8) -> str:
    """Try to pull article full text. Falls back to empty string."""
    try:
        from newspaper import Article
        a = Article(url)
        a.download()
        a.parse()
        return a.text[:4000]   # cap at 4k chars
    except Exception:
        pass
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True)[:4000]
    except Exception:
        return ''

# ── Financial relevance filter ────────────────────────────────────────────────
FINANCIAL_KEYWORDS = [
    # Markets
    "stock", "share", "market", "nifty", "sensex", "bse", "nse", "nasdaq", "dow",
    "s&p", "nyse", "rally", "surge", "fall", "drop", "gain", "loss", "trade",
    # Companies
    "company", "corp", "ltd", "limited", "inc", "earnings", "revenue", "profit",
    "quarterly", "results", "q1", "q2", "q3", "q4", "ipo", "listing",
    # Finance
    "bank", "rbi", "sebi", "fed", "interest rate", "inflation", "gdp", "economy",
    "investment", "investor", "fund", "mutual fund", "etf", "bond", "rupee",
    "dollar", "forex", "crude", "oil", "gold", "commodity",
    # Actions
    "merger", "acquisition", "buyback", "dividend", "split", "deal", "bid",
    "upgrade", "downgrade", "target price", "analyst", "rating",
    # Indian specific
    "crore", "lakh", "sebi", "nse", "bse", "mcx", "lic", "fii", "dii",
]

def is_financial(title: str, text: str = "") -> bool:
    """Return True if article is financially relevant."""
    combined = (title + " " + (text or "")).lower()
    return any(kw in combined for kw in FINANCIAL_KEYWORDS)
