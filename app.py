import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading, asyncio
from bot.main import main
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200)
  self.send_header('Content-type','text/html; charset=utf-8')
  self.end_headers()
  html="""
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0b0e11;color:white;font-family:Arial;text-align:center;margin:0;padding:8px}
.card{background:#1e2329;padding:12px;border-radius:12px;margin:8px}
.price{font-size:28px;font-weight:bold}
iframe{width:100%;height:480px;border:0;border-radius:12px}
.btn{padding:10px 18px;margin:4px;border-radius:8px;border:0;font-weight:bold;cursor:pointer}
.btn-active{background:#f3ba2f;color:black}
.btn-inactive{background:#2b3139;color:white}
.xrp{color:#0ecb81} .btc{color:#f3ba2f} .eth{color:#627eea}
</style>
</head><body>
<h3>🤖 Bot Vicente - XRP BTC ETH - VIVO</h3>
<div style="display:flex;justify-content:center;flex-wrap:wrap">
<div class="card" style="min-width:110px"><div>XRP</div><div class="price xrp" id="xrp">$ --</div></div>
<div class="card" style="min-width:110px"><div>BTC</div><div class="price btc" id="btc">$ --</div></div>
<div class="card" style="min-width:110px"><div>ETH</div><div class="price eth" id="eth">$ --</div></div>
</div>
<div class="card">
<button class="btn" id="bXRP" onclick="show('XRPUSDT','bXRP')" style="background:#f3ba2f;color:black">XRP</button>
<button class="btn" id="bBTC" onclick="show('BTCUSDT','bBTC')" style="background:#2b3139;color:white">BTC</button>
<button class="btn" id="bETH" onclick="show('ETHUSDT','bETH')" style="background:#2b3139;color:white">ETH</button>
<div style="margin-top:10px"><iframe id="tv" src="https://s.tradingview.com/widgetembed/?symbol=BINANCE%3AXRPUSDT&interval=5&theme=dark&style=1&locale=es"></iframe></div>
</div>
<script>
function show(sym,btn){
 document.getElementById('tv').src='https://s.tradingview.com/widgetembed/?symbol=BINANCE%3A'+sym+'&interval=5&theme=dark&style=1&locale=es';
 ['bXRP','bBTC','bETH'].forEach(b=>{document.getElementById(b).style.background='#2b3139';document.getElementById(b).style.color='white'});
 document.getElementById(btn).style.background='#f3ba2f';document.getElementById(btn).style.color='black';
}
async function upd(){
 try{
  let rx=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT'); let jx=await rx.json();
  document.getElementById('xrp').innerText='$'+parseFloat(jx.price).toFixed(4);
  let rb=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'); let jb=await rb.json();
  document.getElementById('btc').innerText='$'+parseFloat(jb.price).toFixed(0);
  let re=await fetch('https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT'); let je=await re.json();
  document.getElementById('eth').innerText='$'+parseFloat(je.price).toFixed(0);
 }catch(e){}
}
setInterval(upd,2000);upd();
</script></body></html>"""
  self.wfile.write(html.encode('utf-8'))
def run_web():
 port=int(os.environ.get("PORT",10000))
 HTTPServer(('0.0.0.0',port),Handler).serve_forever()
if __name__=='__main__':
 threading.Thread(target=run_web,daemon=True).start()
 asyncio.run(main())
