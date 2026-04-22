"""
pipeline.py — Master Pipeline
Fetch → Tag → Dedup → Watchlist → AgentBacklog
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import argparse, time, threading, json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from db_utils import migrate, get_conn

import agentX, agentY, agentZ, agentBacklog, agentWatchlist
import healthcheck; healthcheck.start()

BANNER = """
╔══════════════════════════════════════════════════════╗
║         S T A R K  N E W S  P I P E L I N E         ║
║  X(fetch) → Y(tag) → Z(dedup) → W(watchlist) → AI   ║
╚══════════════════════════════════════════════════════╝"""


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
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🔍 Symbol pipeline for {symbol}: {ts}")
    print(f"{'─'*55}")
    t_total = time.time()

    # Step 1: Fetch
    t = time.time()
    fetched = agentWatchlist.run(symbol=symbol)
    print(f"  ⏱  Watchlist fetch:    {time.time()-t:.1f}s  ({fetched} new articles)")

    # Step 2: Tag (runs BEFORE mark_ready so it can find untagged articles)
    t = time.time()
    tagged = agentY.run(limit=50)
    print(f"  ⏱  Tag layer:          {time.time()-t:.1f}s  ({tagged} tagged)")

    # Step 3: Now mark ready so frontend can see them
    from agentWatchlist import mark_ready
    mark_ready(symbol)

    # Step 4: Dedup
    t = time.time()
    duped = agentZ.run(hours=48)
    print(f"  ⏱  Dedup layer:        {time.time()-t:.1f}s  ({duped} removed)")

    # Step 5: AI backlog
    t = time.time()
    backlog_done = agentBacklog.run()
    print(f"  ⏱  Backlog layer:      {time.time()-t:.1f}s  ({backlog_done} processed)")

    print(f"\n✅ Symbol pipeline for {symbol} complete in {time.time()-t_total:.1f}s\n")
    
def run_once():
    ts = datetime.now().strftime('%d %b %Y, %H:%M:%S')
    print(f"\n{'─'*55}")
    print(f"🚀 Pipeline run started: {ts}")
    print(f"{'─'*55}")
    t_total = time.time()

    t = time.time()
    fetched = agentX.run(parallel=True)
    print(f"  ⏱  Fetch layer:        {time.time()-t:.1f}s  ({fetched} new articles)")

    t = time.time()
    tagged = agentY.run(limit=500)
    print(f"  ⏱  Tag layer:          {time.time()-t:.1f}s  ({tagged} tagged)")

    t = time.time()
    duped = agentZ.run(hours=48)
    print(f"  ⏱  Dedup layer:        {time.time()-t:.1f}s  ({duped} removed)")

    t = time.time()
    watchlist_saved = agentWatchlist.run()
    print(f"  ⏱  Watchlist layer:    {time.time()-t:.1f}s  ({watchlist_saved} new articles)")

    t = time.time()
    backlog_done = agentBacklog.run()
    print(f"  ⏱  Backlog layer:      {time.time()-t:.1f}s  ({backlog_done} processed)")

    print(f"\n✅ Pipeline complete in {time.time()-t_total:.1f}s\n")


# ── Trigger server — listens for search requests from gramblefinal ────────────
class TriggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/trigger':
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            try:
                symbol = json.loads(body).get('symbol', '').upper()
            except Exception:
                symbol = ''

            if symbol:
                print(f'🔍 Search trigger received for {symbol}')
                t = threading.Thread(target=run_for_symbol, args=(symbol,), daemon=True)
                t.start()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'symbol': symbol}).encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, *args):
        pass


def start_trigger_server():
    port = int(os.environ.get('TRIGGER_PORT', 8082))
    server = HTTPServer(('0.0.0.0', port), TriggerHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f'✅ Trigger server on port {port}')


def main():
    print(BANNER)

    parser = argparse.ArgumentParser()
    parser.add_argument('--loop',     action='store_true')
    parser.add_argument('--interval', type=int, default=3)
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

    # ── Start trigger server in background ───────────────────────────────
    start_trigger_server()

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