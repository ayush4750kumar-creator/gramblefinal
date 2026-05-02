"""
fetch_utils.py — Shared helpers for RSS parsing, article scraping, and symbol matching.
"""
import feedparser, requests, re, time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# ── Default fetch window — only articles published in last 1 hour ─────────────
FETCH_WINDOW_HOURS = 1

def is_recent(pub, hours: int = None) -> bool:
    """Returns True only if article was published within `hours` hours.
    Defaults to FETCH_WINDOW_HOURS (1hr) if not specified."""
    window = hours if hours is not None else FETCH_WINDOW_HOURS
    try:
        if isinstance(pub, str):
            for fmt in (
                '%Y-%m-%d %H:%M:%S',
                '%a, %d %b %Y %H:%M:%S %z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%SZ',
                '%d %b %Y %H:%M:%S %z',
            ):
                try:
                    pub = datetime.strptime(pub, fmt)
                    break
                except ValueError:
                    continue
        if isinstance(pub, datetime):
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - pub
            return age <= timedelta(hours=window)
    except Exception:
        pass
    # If we can't parse the date, let it through to avoid dropping valid articles
    return True

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

# ── Headers — NSE/BSE require Referer + Accept or they return empty bodies ────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "en-US,en;q=0.9",
    "Accept-Encoding":  "gzip, deflate, br",
    "Connection":       "keep-alive",
}

# NSE specifically requires a Referer and a warmed-up session cookie.
# Call nse_session() once and reuse the returned Session object.
def nse_session() -> requests.Session:
    """
    Return a requests.Session with NSE cookies set.
    NSE returns empty body (causes JSON parse errors) without a valid session.
    """
    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Referer": "https://www.nseindia.com/",
    })
    try:
        # Warm up: hit the homepage to get session cookies
        session.get("https://www.nseindia.com", timeout=8)
        time.sleep(0.5)
        # Second hit to the market data page seeds more cookies
        session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=8)
        time.sleep(0.3)
    except Exception:
        pass  # Carry on with whatever cookies we got
    return session

# BSE API requires these specific headers to return JSON instead of empty body
BSE_HEADERS = {
    **HEADERS,
    "Referer":  "https://www.bseindia.com/",
    "Origin":   "https://www.bseindia.com",
}

def safe_json(resp: requests.Response, label: str):
    """
    Parse JSON from a response safely.
    Prints a clear error and returns None if the body is empty or not JSON.
    This prevents the 'Expecting value: line 1 column 1' crash.
    """
    raw = resp.text.strip()
    if not raw:
        print(f"  ⚠  {label}: empty response body (HTTP {resp.status_code})")
        return None
    if raw.startswith("<"):
        print(f"  ⚠  {label}: got HTML instead of JSON (HTTP {resp.status_code}) — possible auth wall")
        return None
    try:
        return resp.json()
    except Exception as e:
        print(f"  ⚠  {label}: JSON parse error — {e}")
        return None

def fetch_rss(url: str, source_name: str, timeout=8) -> list:
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

def extract_symbol(text: str, title: str = "") -> str:
    """Only tag symbol if article is primarily about one company."""
    search_text = (title or text or "").lower()[:300]
    matches = []
    for symbol, variants in COMPANY_MAP.items():
        for v in variants:
            if re.search(r"\b" + re.escape(v) + r"\b", search_text):
                matches.append(symbol)
                break
    if len(matches) == 1:
        return matches[0]
    return ""

def is_after_hours(dt_str: str) -> int:
    """Return 1 if the article was published outside 9:00–15:30 IST."""
    try:
        dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
        ist_hour = (dt.hour + 5) % 24
        ist_min  = dt.minute + 30
        if ist_min >= 60:
            ist_hour += 1
            ist_min  -= 60
        total = ist_hour * 60 + ist_min
        return 0 if (9 * 60 <= total <= 15 * 60 + 30) else 1
    except Exception:
        return 0

def fetch_article_text(url: str, timeout=3) -> str:
    """Try to pull article full text. Falls back to empty string."""
    try:
        from newspaper import Article
        a = Article(url)
        a.download()
        a.parse()
        return a.text[:4000]
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
    "stock", "share", "market", "nifty", "sensex", "bse", "nse", "nasdaq", "dow",
    "s&p", "nyse", "rally", "surge", "fall", "drop", "gain", "loss", "trade",
    "company", "corp", "ltd", "limited", "inc", "earnings", "revenue", "profit",
    "quarterly", "results", "q1", "q2", "q3", "q4", "ipo", "listing",
    "bank", "rbi", "sebi", "fed", "interest rate", "inflation", "gdp", "economy",
    "investment", "investor", "fund", "mutual fund", "etf", "bond", "rupee",
    "dollar", "forex", "crude", "oil", "gold", "commodity",
    "merger", "acquisition", "buyback", "dividend", "split", "deal", "bid",
    "upgrade", "downgrade", "target price", "analyst", "rating",
    "crore", "lakh", "sebi", "nse", "bse", "mcx", "lic", "fii", "dii",
]

def is_financial(title: str, text: str = "") -> bool:
    """Return True if article is financially relevant."""
    combined = (title + " " + (text or "")).lower()
    return any(kw in combined for kw in FINANCIAL_KEYWORDS)