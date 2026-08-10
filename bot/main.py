import os, json, httpx, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
T = os.getenv('TELEGRAM_TOKEN','')
B = 'https://api.telegram.org/bot' + T
F = '/data/bot_data.json' if os.path.exists('/data') else '/tmp/bot_data.json'
DASH_URL = "https://telegram-bot-cijp.onrender.com/dashboard"
MONEDAS = ['BTC','ETH','SOL','XRP','DOGE','AVAX','LINK','ADA']
IDS = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple","DOGE":"dogecoin","AVAX":"avalanche-2","LINK":"chainlink","ADA":"cardano"}
BASE = 50

def L():
    try:
        if os.path.exists(F):
            d=json.load(open(F))
            d.setdefault('b',2000); d.setdefault('h',{}); d.setdefault('hs',[])
            d.setdefault('auto',False); d.setdefault('ganancia_total',0)
            d.setdefault('total_trades',0); d.setdefault('alert_users',[])
            d.setdefault('historial_diario',[]); d.setdefault('ganancia_hoy',0)
            d.setdefault('trades_hoy',0); d.setdefault('fecha_hoy',time.strftime('%Y-%m-%d'))
            d.setdefault('inicial',2000)
            return d
    except: pass
    return {'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':[],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000}

def S(s):
    try: json.dump(s, open(F,'w'))
    except: pass

async def P(m):
    # 1. Bybit
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r=await c.get(f'https://api.bybit.com/v5/market/tickers?category=spot&symbol={m}USDT')
            price=float(r.json()['result']['list'][0]['lastPrice'])
            if price>0: return price
    except: pass
    # 2. CoinGecko sin f-string roto
    try:
        coin_id=IDS.get(m)
        async with httpx.AsyncClient(timeout=6) as c:
            url=f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd'
            r=await c.get(url)
            return float(r.json()[coin_id]['usd'])
    except: pass
    # 3. Coinbase
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r=await c.get(f'https://api.coinbase.com/v2/prices/{m}-USD/spot')
            return float(r.json()['data']['amount'])
    except:
        return 0

async def CANDLES(m):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r=await c.get(f'https://api.bybit.com/v5/market/kline?category=spot&symbol={m}USDT&interval=60&limit=100')
            data=r.json()['result']['list']
            closes=[float(x[4]) for x in data[::-1]]
            if len(closes)>=50: return closes
    except: pass
    return []

def ema(a,n):
    if len(a)<n: return []
    k=2/(n+1); s=sum(a[:n])/n; o=[s]
    for x in a[n:]: o.append(x*k+o[-1]*(1-k))
    return o

def rsi(a):
    if len(a)<15: return 50
    g=l=0
    for i in range(len(a)-14,len(a)):
        d=a[i]-a[i-1]
        if d>0: g+=d
        else: l-=d
    return 100-100/(1+g/l) if l!=0 else 70

async def SCORE(sym):
    cl=await CANDLES(sym); pr=await P(sym)
    if not cl or len(cl)<50:
        return {'p':pr,'score':60 if pr>0 else 0,'rsi':50,'tend':'LATERAL'}
    cl[-1]=pr if pr>0 else cl[-1]
    e9=ema(cl,9); e21=ema(cl,21); r=rsi(cl)
    sc=0
    if 20<=r<=45: sc+=40
    if e9 and e21 and e9[-1]>e21[-1]: sc+=30
    if cl[-1]>e9[-1]: sc+=20
    tend="SUBE" if e9 and e21 and e9[-1]>e21[-1] else "BAJA"
    return {'p':pr,'score':min(100,sc+20),'rsi':r,'tend':tend}

@app.get('/api/prices')
async def api_prices():
    out={}
    for m in MONEDAS:
        out[m]=await P(m)
    return JSONResponse(out)

@app.get('/dashboard', response_class=HTMLResponse)
async def dash():
    s=L()
    html="""
<html><head><meta name=viewport content='width=device-width,initial-scale=1'>
<style>
body{background:#080b14;color:#fff;font-family:system-ui;margin:0;padding:10px}
.header{border:1.5px solid #00ffcc55;border-radius:20px;padding:12px;background:#0e1324;display:flex;justify-content:space-between}
.top{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:12px 0}
.box{background:#0f1326;border:1px solid #1e2a5a;border-radius:18px;padding:14px}
.big{font-size:22px;font-weight:900}.g{color:#00ff88}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.coin{border-radius:16px;padding:12px;border:1.5px solid #00ff88;background:#11182c;display:flex;justify-content:space-between}
</style></head><body>
<div class=header><b style='color:#5dfdcb'>V1005 FIXED</b><div style='background:#ffdd57;color:#000;padding:6px 12px;border-radius:20px;font-weight:900'>$2000</div></div>
<div class=top>
<div class=box><small>💰 Saldo</small><div class=big>""" + str(int(s['b'])) + """</div></div>
<div class=box><small>📊 Total</small><div class=big id=total>""" + str(int(s['b'])) + """</div></div>
<div class=box><small>🤖 Auto</small><div class=big style='color:#00ff88'>""" + ('ON' if s['auto'] else 'OFF') + """</div></div>
</div>
<div class=grid id=grid><div style='grid-column:1/-1;text-align:center;padding:20px'>Cargando precios...</div></div>
<script>
async function load(){
  let r=await fetch('/api/prices'); let data=await r.json();
  let grid=document.getElementById('grid'); grid.innerHTML='';
  for(let k in data){
    let price=data[k]; if(price==0) price='Error';
    else price='$'+price;
    grid.innerHTML+=`<div class=coin><div><b>${k}</b><br>${price}</div><div><b>SCORE 60</b><br>HOLD</div></div>`;
  }
}
load(); setInterval(load, 30000);
</script>
</body></html>
"""
    return HTMLResponse(html)

@app.get('/check')
async def check(): return {"ok":"V1005 sin syntax error"}

@app.api_route('/', methods=['GET','POST'])
@app.api_route('/webhook', methods=['GET','POST'])
async def wh(req:Request):
    try: q=await req.json()
    except: q={}
    cid=q.get('message',{}).get('chat',{}).get('id')
    if not cid: return {'ok':1}
    s=L()
    if cid not in s['alert_users']: s['alert_users'].append(cid); S(s)
    t=(q.get('message',{}).get('text') or '').upper().strip()
    if 'RESET' in t:
        S({'b':2000,'h':{},'hs':[],'auto':False,'ganancia_total':0,'total_trades':0,'alert_users':s['alert_users'],'historial_diario':[],'ganancia_hoy':0,'trades_hoy':0,'fecha_hoy':time.strftime('%Y-%m-%d'),'inicial':2000})
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(B+'/sendMessage',json={'chat_id':cid,'text':"♻️ RESET $2000 V1005 FIXED"})
        return {'ok':1}
    if t in MONEDAS:
        pr=await P(t)
        sc=await SCORE(t)
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(B+'/sendMessage',json={'chat_id':cid,'text':f"📊 {t} ${pr}\nSCORE {sc['score']} RSI {int(sc['rsi'])} {sc['tend']}","reply_markup":{"inline_keyboard": [[{"text":"📊 ABRIR DASHBOARD","url":DASH_URL}]]}})
        return {'ok':1}
    return {'ok':1}
