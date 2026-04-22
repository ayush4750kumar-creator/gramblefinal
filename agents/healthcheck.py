import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import subprocess
import sys

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_POST(self):
        if self.path.startswith('/trigger'):
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            try:
                data   = json.loads(body)
                symbol = data.get('symbol', '').upper()
            except Exception:
                symbol = ''

            if symbol:
                print(f'🔍 Trigger received for {symbol}')
                pipeline_path = os.path.join(os.path.dirname(__file__), 'pipeline.py')
                subprocess.Popen(
                    [sys.executable, pipeline_path, '--symbol', symbol],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'symbol': symbol}).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'missing symbol')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass

def start():
    port = int(os.environ.get('PORT', 8081))
    server = HTTPServer(('0.0.0.0', port), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f'✅ Healthcheck server on port {port}')