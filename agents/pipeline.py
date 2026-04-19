"""
pipeline.py — Master Pipeline
Flow: AgentX (fetch) → AgentY (tag) → AgentZ (dedup) → AgentGroq (sentiment+summary+ready)
Articles only appear on website after AgentGroq marks them is_ready=true.

Usage:
  python agents/pipeline.py --loop --interval 5
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


def get_unprocessed_articles(limit=200):
    """Get articles that haven't been processed by Groq yet."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, title, full_text FROM articles
        WHERE (is_ready IS NULL OR is_ready = false)
        AND (is_duplicate IS NULL OR is_duplicate = false)
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def run_once():
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🚀 Pipeline run started: {ts}")
    print(f"{'─'*55}")

    t_total = time.time()

    # ── Layer 1: Fetch new articles (saved with is_ready=false) ──────────────
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

    # ── Layer 4: Groq — sentiment + summary + mark ready ─────────────────────
    t = time.time()
    articles = get_unprocessed_articles(limit=200)
    processed = agentGroq.run(articles)
    print(f"  ⏱  Groq layer:     {time.time()-t:.1f}s  ({processed} processed)")

    elapsed = time.time() - t_total
    print(f"\n✅ Pipeline complete in {elapsed:.1f}s\n")


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description='Stark News Pipeline')
    parser.add_argument('--loop',     action='store_true')
    parser.add_argument('--interval', type=int, default=5)
    args = parser.parse_args()

    print("\n🗄️  Checking database schema...")
    migrate()

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