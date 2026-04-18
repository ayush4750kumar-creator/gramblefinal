"""
db_utils.py — Shared DB layer for the new agent pipeline.
Reads/writes to the existing stockpulse SQLite DB without breaking anything.
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'stockpulse-backend', 'database', 'stockpulse.db')

NEW_COLS = [
    ("tag_feed",         "TEXT"),    # 'company' | 'global'
    ("tag_category",     "TEXT"),    # 'news' | 'opinion' | 'analysis' | 'official' | 'after_hours'
    ("tag_after_hours",  "INTEGER"), # 1 if published outside 9–15:30 IST
    ("tag_source_name",  "TEXT"),    # clean display name e.g. "Economic Times"
    ("sentiment_label",  "TEXT"),    # 'bullish' | 'bearish' | 'neutral'
    ("sentiment_reason", "TEXT"),    # one-line reason
    ("summary_60w",      "TEXT"),    # ≤ 60 word summary
    ("agent_source",     "TEXT"),    # which agent fetched it: 'A'..'G'
    ("is_duplicate",     "INTEGER"), # 1 = deduplicated away
    ("full_text",        "TEXT"),    # full article body for processing
]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate():
    """Adds new columns to existing news table. Safe to run multiple times."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("PRAGMA table_info(news)")
    existing = {row[1] for row in c.fetchall()}
    for col, typ in NEW_COLS:
        if col not in existing:
            try:
                c.execute(f"ALTER TABLE news ADD COLUMN {col} {typ}")
                print(f"  ✅ Added column: {col}")
            except Exception as e:
                print(f"  ⚠  {col}: {e}")
    conn.commit()
    conn.close()
    print("DB migration complete.")

def save_articles(articles: list) -> int:
    """Insert articles. Skips existing URLs. Returns count saved."""
    if not articles:
        return 0
    conn = get_conn()
    c = conn.cursor()
    # discover what columns actually exist so we never crash on schema mismatch
    c.execute("PRAGMA table_info(news)")
    existing_cols = {row[1] for row in c.fetchall()}
    saved = 0
    for art in articles:
        try:
            if not art.get('url'):
                continue
            c.execute("SELECT id FROM news WHERE url = ?", (art['url'],))
            if c.fetchone():
                continue
            allowed = {k: v for k, v in art.items() if k in existing_cols}
            cols_str = ', '.join(allowed.keys())
            placeholders = ', '.join(['?'] * len(allowed))
            c.execute(f"INSERT INTO news ({cols_str}) VALUES ({placeholders})", list(allowed.values()))
            saved += 1
        except Exception as e:
            pass
    conn.commit()
    conn.close()
    return saved

def update_article(article_id: int, updates: dict):
    conn = get_conn()
    c = conn.cursor()
    if not updates:
        return
    set_clause = ', '.join(f"{k} = ?" for k in updates)
    c.execute(f"UPDATE news SET {set_clause} WHERE id = ?", list(updates.values()) + [article_id])
    conn.commit()
    conn.close()

def get_pending_tag(limit=300):
    """Articles that haven't been tagged yet by agentY."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, symbol, title, url, source, published_at, full_text
        FROM news
        WHERE (tag_category IS NULL OR tag_category = '')
          AND (is_duplicate IS NULL OR is_duplicate = 0)
        ORDER BY published_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_pending_dedup(hours=48):
    """Recent non-duplicate articles for dedup pass."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, summary_60w, full_text, url
        FROM news
        WHERE (is_duplicate IS NULL OR is_duplicate = 0)
          AND datetime(published_at) > datetime('now', ? || ' hours')
        ORDER BY published_at DESC
    """, (f"-{hours}",))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_pending_sentiment(limit=200):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, full_text, symbol, tag_feed
        FROM news
        WHERE (sentiment_label IS NULL OR sentiment_label = '')
          AND (is_duplicate IS NULL OR is_duplicate = 0)
        ORDER BY published_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_pending_summary(limit=200):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, full_text, url
        FROM news
        WHERE (summary_60w IS NULL OR summary_60w = '')
          AND (is_duplicate IS NULL OR is_duplicate = 0)
        ORDER BY published_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
