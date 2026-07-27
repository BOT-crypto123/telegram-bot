import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import asyncio
from bot.main import main

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot XRP - Vicente</title>
<style>
body{background:#0b0e11;color:white;font-family:Arial;text-align:center;margin:0;padding:10px}
.card{background:#1e2329;padding:15px;border-radius:12px;margin:12px 0}
.price{font-size:36px;color:#0ecb81;font-weight:bold}
.live{color:#0ecb81;font-size:14px}
</style>
</head>
<body>
<h2>🤖 Bot XRP - Vicente <span class="live">● VIVO 24/7</span></h2>
<div class="card">
<div>Precio XRP / USDT (En Vivo)</div>
<div class="price" id="price">$ --</div>
<div>El bot sigue trabajando en Telegram</div>
</div>
<div class="card">
<div id="tradingview" style="height:500px"></div>
<script src="https://s.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({
  "width": "100%",
  "height": 500,
  "symbol": "BINANCE:XRPUSDT",
  "interval": "5",
  "timezone": "America/Mexico_City",
  "theme": "dark",
  "style": "1",
  "locale": "es",
  "container_id": "tradingview"
});
</script>
</div>
<script>
async function update(){
  try{
    let r = await fetch('https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT');
    let d = await r.json();
    document.getElementById('price').innerText = '$ ' + parseFloat(d.price).toFixed(4);
  }catch(e){}
}
setInterval(update, 3000);
update();
</script>
</body>
</html>
        """
        self.wfile.write(html.encode('utf-8'))

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
