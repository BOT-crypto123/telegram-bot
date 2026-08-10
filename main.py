import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']

async def get_price(m):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT')
            return float(r.json()['result']['list'][0]['lastPrice'])
    except:
        return 0

@app.get('/')
def home():
    return {"status": "LIVE V1011", "dashboard": "/dashboard"}

@app.get('/api/data')
async def api_data():
    out = {}
    for m in MONEDAS:
        out[m] = await get_price(m)
    return JSONResponse(out)

@app.get('/dashboard', response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<style>
body{background:#080b14;color:#fff;font-family:system-ui;padding:12px;margin:0}
.header{border:2px solid #00ffcc88;border-radius:20px;padding:15px;background:#0e1324;display:flex;justify-content:space-between;align-items:center}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px}
.coin{border:1.5px solid #00ff88;background:#11182c;border-radius:18px;padding:15px;text-align:center}
.big{font-size:20px;font-weight:900;margin:6px 0}
</style></head><body>
<div class=header><b style='color:#5dfdcb'>V1011 PUTERO LIVE</b><div style='background:#ffdd57;color:#000;padding:8px 14px;border-radius:20px;font-weight:900'>$2000</div></div>
<div class=grid id=grid><div style='grid-column:1/-1;padding:40px;text-align:center'>Cargando Bybit...</div></div>
<script>
async function load(){
 let r=await fetch('/api/data'); let d=await r.json();
 let g=document.getElementById('grid'); g.innerHTML='';
 for(let k in d){ g.innerHTML+=`<div class=coin><b>${k}</b><div class=big>$${Number(d[k]).toLocaleString()}</div><div style='color:#00ff88'>SCORE 75 BUY</div></div>`; }
}
load(); setInterval(load,15000);
</script>
</body></html>
""")

@app.post('/webhook')
async def webhook(req: Request):
    try:
        data = await req.json()
        print(data)
    except:
        pass
    return {"ok": True}

@app.get('/webhook')
def webhook_get():
    return {"ok": True}
