"""
pipeline.py — Master Pipeline (Fresh Start)
Flow: AgentX (fetch) → AgentY (tag) → AgentZ (dedup) → AgentGroq (sentiment+summary+ready)
- Clears all articles on first boot (fresh start)
- Only processes newly fetched articles (no backlog)
- Runs every 3 minutes

Usage:
  python agents/pipeline.py --loop --interval 3
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse, time
from datetime import datetime
from db_utils import migrate, get_conn
import psycopg2.extras

import agentX, agentY, agentZ, agentGroq
import healthcheck; healthcheck.start()

BANNER = """
╔══════════════════════════════════════════════════════╗
║         S T A R K  N E W S  P I P E L I N E         ║
║   X(fetch) → Y(tag) → Z(dedup) → Groq(AI+ready)     ║
╚══════════════════════════════════════════════════════╝"""


def clear_all_articles():
    """Wipe entire articles table for a fresh start."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("TRUNCATE TABLE articles RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()
    print("🗑️  Cleared all articles from DB — fresh start!")


def get_unprocessed_articles(limit=50):
    """Get only recently added unprocessed articles."""
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text FROM articles
        WHERE (is_ready IS NULL OR is_ready = false)
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def run_once():
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🚀 Pipeline run started: {ts}")
    print(f"{'─'*55}")

    t_total = time.time()

    # ── Layer 1: Fetch ────────────────────────────────────────────────────────
    t = time.time()
    fetched = agentX.run(parallel=True)
    print(f"  ⏱  Fetch layer:    {time.time()-t:.1f}s  ({fetched} new articles)")

    # ── Layer 2: Tag ──────────────────────────────────────────────────────────
    t = time.time()
    tagged = agentY.run(limit=500)
    print(f"  ⏱  Tag layer:      {time.time()-t:.1f}s  ({tagged} tagged)")

    # ── Layer 3: Deduplicate ──────────────────────────────────────────────────
    t = time.time()
    duped = agentZ.run(hours=48)
    print(f"  ⏱  Dedup layer:    {time.time()-t:.1f}s  ({duped} removed)")

    # ── Layer 4: Groq — only process what's new, no backlog ──────────────────
    t = time.time()
    articles = get_unprocessed_articles(limit=50)
    processed = agentGroq.run(articles)
    print(f"  ⏱  Groq layer:     {time.time()-t:.1f}s  ({processed} processed)")

    elapsed = time.time() - t_total
    print(f"\n✅ Pipeline complete in {elapsed:.1f}s\n")


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description='Stark News Pipeline')
    parser.add_argument('--loop',     action='store_true')
    parser.add_argument('--interval', type=int, default=3)
    parser.add_argument('--no-clear', action='store_true', help='Skip DB clear on startup')
    args = parser.parse_args()

    print("\n🗄️  Checking database schema...")
    migrate()

    # Fresh start — wipe old backlog unless --no-clear is passed
    if not args.no_clear:
        clear_all_articles()

    if args.loop:
        print(f"\n⏰ Loop mode: every {args.interval} minutes. Ctrl+C to stop.\n")
        while True:
            try:
                run_once()
                print(f"💤 Sleeping {args.interval} min...\n")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n🛑 Pipeline stopped.")
                break
            except Exception as e:
                print(f"\n⚠  Pipeline error: {e} — retrying in {args.interval} min")
                time.sleep(args.interval * 60)
    else:
        run_once()


if __name__ == '__main__':
    main()