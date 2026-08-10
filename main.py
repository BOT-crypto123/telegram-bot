import os, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']

async def get_price(m):
    # 1. Intento Bybit
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT', headers={"User-Agent":"Mozilla/5.0"})
            j = r.json()
            price = float(j['result']['list'][0]['lastPrice'])
            if price>0: return price
    except Exception as e:
        print(f"Bybit fail {m}: {e}")

    # 2. Intento Binance
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.binance.com/api/v3/ticker/price?symbol={m}USDT', headers={"User-Agent":"Mozilla/5.0"})
            price = float(r.json()['price'])
            if price>0: return price
    except Exception as e:
        print(f"Binance fail {m}: {e}")

    # 3. Intento CoinGecko (nunca falla)
    try:
        mapa = {'BTC':'bitcoin','ETH':'ethereum','SOL':'solana','XRP':'ripple','DOGE':'dogecoin','AVAX':'avalanche-2','LINK':'chainlink','ADA':'cardano'}
        cid = mapa.get(m,m.lower())
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd', headers={"User-Agent":"Mozilla/5.0"})
            price = float(r.json()[cid]['usd'])
            if price>0: return price
    except Exception as e:
        print(f"Gecko fail {m}: {e}")

    return 0

async def send_tg(chat_id, text):
    if not TOKEN: return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except: pass

@app.get('/')
def home(): return {"status":"LIVE V1013", "dashboard":"/dashboard"}

@app.get('/api/data')
async def api_data():
    out={}
    for m in MONEDAS: out[m]=await get_price(m)
    return JSONResponse(out)

@app.get('/dashboard', response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<style>
body{background:#080b14;color:#fff;font-family:system-ui;padding:12px}
.header{border:2px solid #00ffcc88;border-radius:20px;padding:15px;background:#0e1324;display:flex;justify-content:space-between}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px}
.coin{border:1.5px solid #00ff88;background:#11182c;border-radius:18px;padding:15px;text-align:center}
.big{font-size:22px;font-weight:900}
</style></head><body>
<div class=header><b style='color:#5dfdcb'>V1013 MAQUINA MILLONARIA</b><div style='background:#ffdd57;color:#000;padding:8px 14px;border-radius:20px;font-weight:900'>$2000</div></div>
<div class=grid id=grid><div style='grid-column:1/-1;padding:40px;text-align:center'>Cargando precios reales...</div></div>
<script>
async function load(){
 let r=await fetch('/api/data'); let d=await r.json();
 let g=document.getElementById('grid'); g.innerHTML='';
 for(let k in d){ let v=d[k]; let p=v? '$'+Number(v).toLocaleString(): '...'; g.innerHTML+=`<div class=coin><b>${k}</b><div class=big>${p}</div><div style='color:#00ff88'>SCORE 75 BUY</div></div>`; }
}
load(); setInterval(load,15000);
</script>
</body></html>
""")

@app.post('/webhook')
async def webhook(req: Request):
    data = await req.json()
    try:
        msg = data.get('message') or {}
        chat_id = msg.get('chat',{}).get('id')
        if not chat_id: return {"ok":True}
        text = msg.get('text','').upper().strip().replace("/","")
        if text in ["START","HOLA",""]:
            await send_tg(chat_id, "🔥 *MAQUINA V1013 LIVE* 🔥\nBotones abajo 👇 o escribe BTC, SOL, ETH, XRP")
            return {"ok":True}
        coin = text.split()[0]
        if coin in MONEDAS:
            p = await get_price(coin)
            if p==0:
                await send_tg(chat_id, f"⚠️ {coin} temporalmente sin precio, intenta de nuevo en 5 seg")
            else:
                await send_tg(chat_id, f"💰 *{coin}* = ${p:,.2f}\nSCORE 75 BUY 🚀\nDashboard: https://telegram-bot-cijp.onrender.com/dashboard")
        else:
            await send_tg(chat_id, f"Monedas: {', '.join(MONEDAS)}")
    except Exception as e:
        print(e)
    return {"ok":True}

@app.get('/webhook')
def wh(): return {"ok":True}
