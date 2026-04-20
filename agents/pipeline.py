"""
pipeline.py — Master Pipeline
Fetch → Tag → Dedup → AgentBacklog (up to 50 parallel sub-agents)

AgentBacklog spawns one sub-agent per Groq key (GROQ_API_KEY_1 to GROQ_API_KEY_50).
Each sub-agent owns its key exclusively — zero contention.
With 50 keys: ~25 seconds to process 600 articles.

Usage:
  python agents/pipeline.py --loop --interval 3
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse, time
from datetime import datetime
from db_utils import migrate, get_conn

import agentX, agentY, agentZ, agentBacklog
import healthcheck; healthcheck.start()

BANNER = """
╔══════════════════════════════════════════════════════╗
║         S T A R K  N E W S  P I P E L I N E         ║
║     X(fetch) → Y(tag) → Z(dedup) → Backlog(AI)      ║
╚══════════════════════════════════════════════════════╝"""


def clear_all_articles():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("TRUNCATE TABLE articles RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()
    print("🗑️  Cleared all articles from DB — fresh start!")


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

    # ── Layer 3: Dedup ────────────────────────────────────────────────────────
    t = time.time()
    duped = agentZ.run(hours=48)
    print(f"  ⏱  Dedup layer:    {time.time()-t:.1f}s  ({duped} removed)")

    # ── Layer 4: Backlog — all unprocessed articles, parallel sub-agents ──────
    t = time.time()
    backlog_done = agentBacklog.run()
    print(f"  ⏱  Backlog layer:  {time.time()-t:.1f}s  ({backlog_done} processed)")

    elapsed = time.time() - t_total
    print(f"\n✅ Pipeline complete in {elapsed:.1f}s\n")


def main():
    print(BANNER)

    parser = argparse.ArgumentParser()
    parser.add_argument('--loop',     action='store_true')
    parser.add_argument('--interval', type=int, default=3)
    parser.add_argument('--clear', action='store_true')
    args = parser.parse_args()

    print("\n🗄️  Checking database schema...")
    migrate()

   if args.clear:
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