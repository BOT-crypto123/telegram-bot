import os, json, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
F = '/tmp/data.json'
DASH_URL = "https://telegram-bot-cijp.onrender.com/dashboard"

def L():
    try:
        if os.path.exists(F): return json.load(open(F))
    except: pass
    return {'b':2000,'h':{}}

async def P(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT')
            return float(r.json()['result']['list'][0]['lastPrice'])
    except: return 0

@app.get('/api/data')
async def api_data():
    out={}
    for m in MONEDAS: out[m]=await P(m)
    return JSONResponse(out)

@app.get('/dashboard', response_class=HTMLResponse)
async def dashboard():
    html = """
<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<style>
body{background:#080b14;color:#fff;font-family:system-ui;padding:10px;margin:0}
.header{border:2px solid #00ffcc77;border-radius:20px;padding:15px;background:#0e1324;display:flex;justify-content:space-between;align-items:center}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px}
.coin{border:1.5px solid #00ff88;background:#11182c;border-radius:18px;padding:15px;text-align:center}
.big{font-size:22px;font-weight:900}
</style></head><body>
<div class=header><b style='color:#5dfdcb'>V1007 PUTERO LIVE</b><div style='background:#ffdd57;color:#000;padding:8px 14px;border-radius:20px;font-weight:900'>$2000</div></div>
<div class=grid id=grid><div style='grid-column:1/-1;padding:30px;text-align:center;opacity:.5'>Cargando precios Bybit...</div></div>
<script>
async function load(){
  let r=await fetch('/api/data'); let d=await r.json();
  let g=document.getElementById('grid'); g.innerHTML='';
  for(let k in d){
    g.innerHTML+=`<div class=coin><b>${k}</b><div class=big>$${d[k]}</div><div style='color:#00ff88'>SCORE 75</div></div>`;
  }
}
load(); setInterval(load,15000);
</script>
</body></html>
"""
    return HTMLResponse(html)

@app.get('/')
async def root():
    return {"status":"BOT LIVE V1007","dashboard":"/dashboard","api":"/api/data"}

@app.api_route('/webhook', methods=['GET','POST'])
async def webhook(req:Request):
    return {"ok":1}
"""
    return HTMLResponse(html)

@app.get('/')
def home():
    return {"ok":"V1007 LIVE","dashboard":"/dashboard"}

@app.api_route('/webhook', methods=['GET','POST'])
async def wh(request: Request):
    return {"ok":1}
