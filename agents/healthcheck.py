import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

_pipeline_fn = None

def set_trigger(fn):
    global _pipeline_fn
    _pipeline_fn = fn

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
            return

        if parsed.path == '/trigger-search':
            params = parse_qs(parsed.query)
            symbol = params.get('symbol', [''])[0].strip().upper()
            if symbol and _pipeline_fn:
                t = threading.Thread(target=_pipeline_fn, args=(symbol,), daemon=True)
                t.start()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f'triggered {symbol}'.encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'missing symbol')
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass

def start(port=8080):
    server = HTTPServer(('0.0.0.0', port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f'✅ Healthcheck server on port {port}')