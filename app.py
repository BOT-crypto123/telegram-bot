from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import asyncio
from bot.main import main

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot vivo 24/7 - Vicente")

def run_web():
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server.serve_forever()

def run_bot():
    asyncio.run(main())

threading.Thread(target=run_web, daemon=True).start()
run_bot()
