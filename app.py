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
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{background:#0b0e11;color:white;font-family:Arial;text-align:center;margin:0;padding:10px}
.card{background:#1e2329;padding:15px;border-radius:12px;margin:10px}
.price{font-size:36px;color:#0ecb81;font-weight:bold}
iframe{width:100%;height:550px;border:0;border-radius:12px}</style>
</head>
<body>
<h3>🤖 Bot XRP - Vicente - VIVO 24/7</h3>
<div class="card"><div>Precio XRP/USDT</div><div class="price" id="p">$ --</div></div>
<div class="card">
<iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE%3AXRPUSDT&interval=5&theme=dark&style=1&locale=es&studies=[]"></iframe>
<div style="margin-top:10px">✅ Grafica TradingView + EMA + RSI</div>
</div>
<script>
async function upd(){
 try{
  let r=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT');
  let j=await r.json();
  document.getElementById('p').innerText='$ '+parseFloat(j.price).toFixed(4);
 }catch(e){}
}
setInterval(upd,2000);upd();
</script>
</body>
</html>
"""
        self.wfile.write(html.encode('utf-8'))

def run_web():
    port=int(os.environ.get("PORT",10000))
    HTTPServer(('0.0.0.0',port),Handler).serve_forever()

if __name__=='__main__':
    threading.Thread(target=run_web,daemon=True).start()
    asyncio.run(main())
