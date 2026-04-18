import os, psycopg2, psycopg2.extras
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def save_articles(articles: list) -> int:
    if not articles:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    saved = 0
    for art in articles:
        try:
            if not art.get('url'):
                continue
            cur.execute("SELECT id FROM articles WHERE url = %s", (art['url'],))
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO articles
                  (symbol, title, url, source, tag_source_name, published_at,
                   full_text, tag_feed, tag_category, agent_source, tag_after_hours)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                art.get('symbol',''),
                art.get('title',''),
                art.get('url',''),
                art.get('source',''),
                art.get('tag_source_name',''),
                art.get('published_at',''),
                art.get('full_text',''),
                art.get('tag_feed','global'),
                art.get('tag_category','news'),
                art.get('agent_source',''),
                art.get('tag_after_hours', 0),
            ))
            saved += 1
        except Exception as e:
            conn.rollback()
            continue
    conn.commit()
    cur.close()
    conn.close()
    return saved

def update_article(article_id: int, updates: dict):
    if not updates:
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        set_clause = ', '.join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE articles SET {set_clause} WHERE id = %s",
            list(updates.values()) + [article_id]
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"  ⚠ update_article error: {e}")
    finally:
        cur.close()
        conn.close()

def get_pending_tag(limit=500):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, symbol, title, url, source, published_at, full_text, agent_source
        FROM articles
        WHERE (tag_category IS NULL OR tag_category = '')
          AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_pending_dedup(hours=48):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, summary_60w, full_text, url, source
        FROM articles
        WHERE (is_duplicate IS NULL OR is_duplicate = false)
          AND published_at >= NOW() - INTERVAL '%s hours'
        ORDER BY published_at DESC
    """ % hours)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_pending_sentiment(limit=300):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text, symbol
        FROM articles
        WHERE (sentiment_label IS NULL OR sentiment_label = '')
          AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_pending_summary(limit=300):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text, url
        FROM articles
        WHERE (summary_60w IS NULL OR summary_60w = '')
          AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY published_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def mark_duplicate(article_id: int):
    update_article(article_id, {'is_duplicate': True})
