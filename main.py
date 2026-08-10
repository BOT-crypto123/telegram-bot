import os, httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']

async def get_price(m):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT')
            return float(r.json()['result']['list'][0]['lastPrice'])
    except:
        return 0

async def send_tg(chat_id, text):
    if not TOKEN: return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except:
        pass

@app.get('/')
def home(): return {"status":"LIVE V1012", "dashboard":"/dashboard"}

@app.get('/api/data')
async def api_data():
    out={}
    for m in MONEDAS: out[m]=await get_price(m)
    return JSONResponse(out)

@app.get('/dashboard', response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<html><head><meta name=viewport content='width=device-width,initial-scale=1'><style>body{background:#080b14;color:#fff;font-family:system-ui;padding:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.coin{border:1px solid #0f8;background:#11182c;border-radius:15px;padding:12px;text-align:center}</style></head><body><h3>V1012 LIVE</h3><div class=grid id=g></div><script>async function l(){let r=await fetch('/api/data');let d=await r.json();let g=document.getElementById('g');g.innerHTML='';for(let k in d)g.innerHTML+=`<div class=coin><b>${k}</b><div>$${Number(d[k]).toLocaleString()}</div></div>`}l();setInterval(l,15000)</script></body></html>""")

@app.post('/webhook')
async def webhook(req: Request):
    data = await req.json()
    try:
        msg = data.get('message') or data.get('edited_message')
        if not msg: return {"ok":True}
        chat_id = msg['chat']['id']
        text = msg.get('text','').upper().strip()

        if text in ["", "/START", "/start"]:
            await send_tg(chat_id, "🔥 *BOT V1012 LIVE* 🔥\nEscribe: BTC, SOL, ETH")
            return {"ok":True}

        coin = text.replace("/","").split()[0]
        if coin in MONEDAS:
            p = await get_price(coin)
            await send_tg(chat_id, f"💰 *{coin}* = ${p:,.2f}\nSCORE 75 BUY\nDashboard: https://telegram-bot-cijp.onrender.com/dashboard")
        else:
            await send_tg(chat_id, f"Escribe una moneda: {', '.join(MONEDAS)}")
    except Exception as e:
        print(e)
    return {"ok":True}

@app.get('/webhook')
def webhook_get(): return {"ok":True}
