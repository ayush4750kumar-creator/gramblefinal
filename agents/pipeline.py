"""
pipeline.py — Master Pipeline
Fetch → Tag → Dedup → Watchlist → AgentBacklog
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse, time, threading
from datetime import datetime
from db_utils import migrate, get_conn

import agentX, agentY, agentZ, agentBacklog, agentWatchlist
from groq_pool import SEARCH_POOL
import healthcheck

BANNER = """
╔══════════════════════════════════════════════════════╗
║         S T A R K  N E W S  P I P E L I N E         ║
║  X(fetch) → W(watchlist) → Y(tag) → Z(dedup) → AI   ║
╚══════════════════════════════════════════════════════╝"""

_running_symbols: set = set()
_running_lock = threading.Lock()

_search_running = threading.Event()


def cleanup_old_articles():
    """Delete articles older than 7 days — runs at the start of every pipeline run."""
    conn = get_conn()
    cur  = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM articles
            WHERE published_at < NOW() - INTERVAL '7 days'
        """)
        deleted = cur.rowcount
        conn.commit()
        print(f"  🗑  Cleaned up {deleted} articles older than 7 days")
    except Exception as e:
        print(f"  ⚠  Cleanup error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def clear_all_articles():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("TRUNCATE TABLE articles RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()
    print("🗑️  Cleared all articles from DB — fresh start!")


def run_for_symbol(symbol: str):
    symbol = symbol.upper()

    with _running_lock:
        if symbol in _running_symbols:
            print(f"⏭  {symbol} already running — skipping duplicate trigger")
            return
        _running_symbols.add(symbol)

    _search_running.set()

    try:
        ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
        print(f"\n{'─'*55}")
        print(f"🔍 Symbol pipeline for {symbol}: {ts}")
        print(f"{'─'*55}")
        t_total = time.time()

        try:
            t = time.time()
            fetched = agentWatchlist.run(symbol=symbol)
            print(f"  ⏱  Watchlist fetch:    {time.time()-t:.1f}s  ({fetched} new articles)")

            t = time.time()
            tagged = agentY.run(limit=50)
            print(f"  ⏱  Tag layer:          {time.time()-t:.1f}s  ({tagged} tagged)")

            t = time.time()
            duped = agentZ.run(hours=48)
            print(f"  ⏱  Dedup layer:        {time.time()-t:.1f}s  ({duped} removed)")

            t = time.time()
            backlog_done = agentBacklog.run(pool=SEARCH_POOL, symbol=symbol, limit=5)
            print(f"  ⏱  Backlog layer:      {time.time()-t:.1f}s  ({backlog_done} processed)")

            from agentWatchlist import mark_ready
            mark_ready(symbol)

            print(f"\n✅ Symbol pipeline for {symbol} complete in {time.time()-t_total:.1f}s\n")

        except Exception as e:
            print(f"\n⚠  Symbol pipeline error for {symbol}: {e}\n")

    finally:
        with _running_lock:
            _running_symbols.discard(symbol)
            if not _running_symbols:
                _search_running.clear()


def run_once():
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🚀 Pipeline run started: {ts}")
    print(f"{'─'*55}")
    t_total = time.time()

    # ── STEP 0: Auto-delete articles older than 7 days ────────────────────────
    try:
        cleanup_old_articles()
    except Exception as e:
        print(f"  ⚠  Cleanup error: {e}")

    # ── STEP 1: Fetch all articles (1-hour window applied inside each agent) ──
    try:
        t = time.time()
        fetched = agentX.run(parallel=True)
        print(f"  ⏱  Fetch layer:        {time.time()-t:.1f}s  ({fetched} new articles)")
    except Exception as e:
        print(f"  ⚠  Fetch layer error: {e}")

    # ── STEP 2: Watchlist ─────────────────────────────────────────────────────
    try:
        t = time.time()
        watchlist_saved = agentWatchlist.run()
        print(f"  ⏱  Watchlist layer:    {time.time()-t:.1f}s  ({watchlist_saved} new articles)")
    except Exception as e:
        print(f"  ⚠  Watchlist layer error: {e}")

    # ── STEP 3: Tag ───────────────────────────────────────────────────────────
    try:
        t = time.time()
        tagged = agentY.run(limit=500)
        print(f"  ⏱  Tag layer:          {time.time()-t:.1f}s  ({tagged} tagged)")
    except Exception as e:
        print(f"  ⚠  Tag layer error: {e}")

    # ── STEP 4: Dedup ─────────────────────────────────────────────────────────
    try:
        t = time.time()
        duped = agentZ.run(hours=48)
        print(f"  ⏱  Dedup layer:        {time.time()-t:.1f}s  ({duped} removed)")
    except Exception as e:
        print(f"  ⚠  Dedup layer error: {e}")

    # Wait for any active symbol search before running main backlog
    if _search_running.is_set():
        print(f"  ⏸  Search pipeline active — waiting before main backlog...")
        _search_running.wait()
        print(f"  ▶️  Search done — resuming main backlog")

    # ── STEP 5: Backlog ───────────────────────────────────────────────────────
    try:
        t = time.time()
        backlog_done = agentBacklog.run()
        print(f"  ⏱  Backlog layer:      {time.time()-t:.1f}s  ({backlog_done} processed)")
    except Exception as e:
        print(f"  ⚠  Backlog layer error: {e}")

    print(f"\n✅ Pipeline complete in {time.time()-t_total:.1f}s\n")


healthcheck.set_trigger(run_for_symbol)
healthcheck.start()


def main():
    print(BANNER)

    parser = argparse.ArgumentParser()
    parser.add_argument('--loop',     action='store_true')
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--clear',    action='store_true')
    parser.add_argument('--symbol',   default='')
    args = parser.parse_args()

    print("\n🗄️  Checking database schema...")
    migrate()

    if args.clear:
        clear_all_articles()

    if args.symbol:
        run_for_symbol(args.symbol)
        return

    if args.loop:
        print(f"\n⏰ Loop mode: every {args.interval} minutes. Ctrl+C to stop.\n")
        while True:
            try:
                run_once()
            except Exception as e:
                print(f"\n⚠  Pipeline error: {e}")
            print(f"💤 Sleeping {args.interval} min...\n")
            time.sleep(args.interval * 60)
    else:
        run_once()


if __name__ == '__main__':
    main()