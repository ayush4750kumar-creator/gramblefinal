import os, psycopg2, psycopg2.extras
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def migrate():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id              SERIAL PRIMARY KEY,
            symbol          TEXT,
            title           TEXT NOT NULL,
            url             TEXT UNIQUE,
            source          TEXT,
            tag_source_name TEXT,
            published_at    TIMESTAMPTZ,
            full_text       TEXT,
            tag_feed        TEXT DEFAULT 'global',
            tag_category    TEXT DEFAULT 'news',
            tag_after_hours INTEGER DEFAULT 0,
            agent_source    TEXT,
            sentiment_label TEXT,
            sentiment_reason TEXT,
            summary_60w     TEXT,
            is_duplicate    BOOLEAN DEFAULT false,
            image_url       TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_articles_symbol ON articles(symbol);
        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
    """)
    conn.commit()
    cur.close(); conn.close()
    print('✅ DB migrated')

def is_financial_article(title, text=""):
    combined = (title + " " + (text or "")).lower()
    return any(kw in combined for kw in FINANCIAL_KEYWORDS)

def save_articles(articles: list) -> int:
    articles = [a for a in articles if is_financial_article(a.get("title",""), a.get("full_text",""))]
    if not articles: return 0
    if not articles: return 0
    conn = get_conn()
    cur = conn.cursor()
    saved = 0
    for a in articles:
        try:
            cur.execute("""
                INSERT INTO articles (symbol, title, url, source, tag_source_name, published_at, full_text, image_url, tag_feed, agent_source)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (url) DO NOTHING
            """, (
                a.get('symbol'), a.get('title'), a.get('url'), a.get('source'),
                a.get('tag_source_name'), a.get('published_at'), a.get('full_text'),
                a.get('image_url'), a.get('tag_feed','global'), a.get('agent_source')
            ))
            saved += cur.rowcount
        except Exception as e:
            print(f'save error: {e}')
    conn.commit()
    cur.close(); conn.close()
    return saved

def update_article(article_id: int, updates: dict):
    if not updates: return
    conn = get_conn()
    cur = conn.cursor()
    cols = ', '.join(f"{k}=%s" for k in updates)
    cur.execute(f"UPDATE articles SET {cols} WHERE id=%s", list(updates.values()) + [article_id])
    conn.commit()
    cur.close(); conn.close()

def get_pending_tag(limit=300):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, url, source FROM articles
        WHERE (tag_category IS NULL OR tag_category = '')
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def get_pending_dedup(hours=48):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, url FROM articles
        WHERE (is_duplicate IS NULL OR is_duplicate = false)
        AND published_at >= NOW() - INTERVAL '%s hours'
        ORDER BY published_at DESC
    """ % hours)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def get_pending_sentiment(limit=200):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text, symbol FROM articles
        WHERE (sentiment_label IS NULL OR sentiment_label = '')
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def get_pending_summary(limit=200):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text, url FROM articles
        WHERE (summary_60w IS NULL OR summary_60w = '')
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

def mark_duplicate(article_id: int):
    update_article(article_id, {'is_duplicate': True})

def delete_old_articles():
    """Delete articles older than 6 days."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM articles WHERE published_at < NOW() - INTERVAL '6 days'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def mark_articles_ready():
    """Mark all processed articles as ready to show in feed."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE articles 
            SET is_ready = true 
            WHERE is_ready IS NOT DISTINCT FROM false
            AND sentiment_label IS NOT NULL 
            AND summary_60w IS NOT NULL
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# ── Financial relevance filter ────────────────────────────────────────────────
FINANCIAL_KEYWORDS = [
    "stock","share","market","nifty","sensex","bse","nse","nasdaq","dow","s&p","nyse",
    "rally","surge","bull","bear","intraday","trading","52-week","circuit","market cap",
    "futures","options","f&o","derivative","expiry","open interest","index","indices",
    "company","corp","ltd","limited","inc","plc","pvt","earnings","revenue","profit",
    "loss","ebitda","net income","quarterly","annual report","results","q1","q2","q3","q4",
    "ipo","listing","delisting","merger","acquisition","takeover","buyout","buyback",
    "dividend","bonus share","stock split","rights issue","board meeting","agm","egm",
    "shareholding","promoter","stake","joint venture","subsidiary","conglomerate",
    "bank","banking","nbfc","credit","loan","lending","npa","bad loan","capital adequacy",
    "rbi","sebi","fed","ecb","central bank","monetary policy","interest rate","repo rate",
    "inflation","cpi","wpi","gdp","fiscal deficit","current account","trade deficit",
    "insurance","lic","pension","mutual fund","sip","nav","aum","etf","bond","debenture",
    "yield","gilt","treasury","rupee","dollar","euro","forex","currency","exchange rate",
    "crude","oil","brent","wti","opec","natural gas","gold","silver","copper","commodity","mcx",
    "investment","investor","fii","dii","fpi","institutional","portfolio","wealth",
    "upgrade","downgrade","target price","analyst","rating","valuation","pe ratio","eps",
    "broker","brokerage","reliance industries","tata","infosys","wipro","hdfc","icici","sbi",
    "adani","bajaj","mahindra","maruti","ongc","ntpc","sunpharma","cipla","drreddy",
    "hcltech","techm","titan","britannia","nestle","itc","hindustan unilever","zomato",
    "paytm","tesla","apple","microsoft","google","nvidia","amazon","meta","netflix",
    "jpmorgan","goldman","samsung","tsmc","intel","amd","budget","tax","gst","tariff",
    "export","import","trade war","trade deal","sanctions","startup","unicorn","funding",
    "venture capital","private equity","real estate","property","housing","reit",
    "solar","wind","renewable","ev","electric vehicle","battery","automobile","auto sales",
    "financial","monetary","fiscal","economic","equity","debt","capital","liquidity",
    "volatility","risk","return","spread","block deal","bulk deal","insider trading",
    "results season","earnings season","guidance","outlook","forecast","recession",
    "rate hike","rate cut","credit rating","moody","fitch","crisil","crore","lakh",
]


