"""
pipeline.py — Master Pipeline
Runs the full chain: AgentX → AgentY → AgentZ → AgentO → AgentP → AgentGroq

Usage:
  python agents/pipeline.py
  python agents/pipeline.py --loop --interval 5
  python agents/pipeline.py --process-only
  python agents/pipeline.py --fetch-online
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse, time
from datetime import datetime
from db_utils import migrate

import agentX, agentY, agentZ, agentO, agentP, agentGroq

BANNER = """
╔══════════════════════════════════════════════════════╗
║         S T A R K  N E W S  P I P E L I N E         ║
║  X(fetch) → Y(tag) → Z(dedup) → O(sentiment)        ║
║           → P(summary) → Groq(AI enhance)            ║
╚══════════════════════════════════════════════════════╝"""


def run_once(process_only: bool = False, fetch_online: bool = False):
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🚀 Pipeline run started: {ts}")
    print(f"{'─'*55}")

    t_total = time.time()

    # ── Layer 1: Fetch ────────────────────────────────────────────────────────
    if not process_only:
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

    # ── Layer 4: Keyword Sentiment (fast fallback) ────────────────────────────
    t = time.time()
    sentimized = agentO.run(limit=300)
    print(f"  ⏱  Sentiment (kw): {time.time()-t:.1f}s  ({sentimized} analysed)")

    # ── Layer 5: Extractive Summary (fast fallback) ───────────────────────────
    t = time.time()
    summarised = agentP.run(limit=300, fetch_online=fetch_online)
    print(f"  ⏱  Summary (ext):  {time.time()-t:.1f}s  ({summarised} summarised)")

    # ── Layer 6: Groq AI Enhancement (English AI quality boost) ──────────────
    t = time.time()
    groq_done = agentGroq.run(sentiment_limit=80, summary_limit=80)
    print(f"  ⏱  Groq AI:        {time.time()-t:.1f}s  ({groq_done} AI-enhanced)")

    elapsed = time.time() - t_total
    print(f"\n✅ Pipeline complete in {elapsed:.1f}s\n")


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description='Stark News Pipeline')
    parser.add_argument('--loop',         action='store_true')
    parser.add_argument('--interval',     type=int, default=5)
    parser.add_argument('--process-only', action='store_true')
    parser.add_argument('--fetch-online', action='store_true')
    args = parser.parse_args()

    print("\n🗄️  Checking database schema...")
    migrate()

    if args.loop:
        print(f"\n⏰ Loop mode: every {args.interval} minutes. Ctrl+C to stop.\n")
        while True:
            try:
                run_once(
                    process_only=args.process_only,
                    fetch_online=args.fetch_online,
                )
                print(f"💤 Sleeping {args.interval} min...\n")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n🛑 Pipeline stopped.")
                break
            except Exception as e:
                print(f"\n⚠  Pipeline error: {e} — retrying in {args.interval} min")
                time.sleep(args.interval * 60)
    else:
        run_once(
            process_only=args.process_only,
            fetch_online=args.fetch_online,
        )


if __name__ == '__main__':
    main()
