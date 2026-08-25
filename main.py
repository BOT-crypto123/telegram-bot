from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json, os

app = FastAPI()

DEFAULT = {
 "disponible_usd":333.77,"bloqueado_usd":187.5,"gan_acum":21.27,
 "disponible_m":20.14,"bloqueado_m":500,"gan_mt5":20.14,
 "max_entradas":8,"max_m":8,"bolas_long":4,"bolas_short":4,"bolas_long_m":4,"bolas_short_m":4,
 "tp":0.3,"sl_pct":2.5,"tp_m":0.5,"sl_m":3.0,"auto":True,"auto_m":True,
 "modo":"AMBOS","modo_m":"AMBOS",
 "coins_activas":{"ADA":True,"AVAX":True,"BNB":True,"BTC":True,"DOGE":True,"ETH":True,"SOL":True,"XRP":True},
 "coins_mt5_activas":{"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True,"EURUSD":True,"GBPUSD":True,"NAS100":True,"GER40":True},
 "pos":[],"pos_m":[],"pos_m_short":[],"historial":[],"historial_m":[]
}

def load():
 try:
  with open("state.json","r") as f:
   s=json.load(f)
   for k,v in DEFAULT.items():
    if k not in s: s[k]=v
   return s
 except: return DEFAULT.copy()

def save(s):
 with open("state.json","w") as f: json.dump(s,f)

def safe_html(fn):
 try:
  if os.path.exists(fn):
   with open(fn,"r",encoding="utf-8") as f: return HTMLResponse(f.read())
 except: pass
 return None

@app.get("/", response_class=HTMLResponse)
async def index():
 s=load()
 tb = float(s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0))
 tm = float(s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0))
 bb = tb / max(1,s.get("max_entradas",8))
 bm = tm / max(1,s.get("max_m",8))
 usdmxn=17.2
 try:
  import requests
  r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=2)
  usdmxn=r.json().get("rates",{}).get("MXN",17.2)
 except: pass
 return HTMLResponse(f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DUAL V5 - FINAL REAL</title>
<style>*{{box-sizing:border-box;font-family:system-ui;margin:0}}body{{background:#000;color:#fff}}
.wrap{{display:flex;width:100vw;min-height:100vh}}.side{{width:50%;padding:8px}}
.left{{background:#080808;border-right:1px solid #1a1a1a}}.right{{background:#0b1326}}
.h{{font-weight:900;font-size:13px}}.hy{{color:#facc15}}.hb{{color:#60a5fa}}.sub{{font-size:10px;opacity:.6;margin-bottom:10px}}
.circle{{width:165px;height:165px;border-radius:50%;margin:15px auto 8px;display:flex;flex-direction:column;justify-content:center;align-items:center}}
.cy{{border:8px solid #facc15;background:radial-gradient(circle,#1a1600,#000);box-shadow:0 0 35px rgba(250,204,21,.6)}}
.cb{{border:8px solid #3b82f6;background:radial-gradient(circle,#0e1a35,#0a1226);box-shadow:0 0 35px rgba(59,130,246,.6)}}
.cap{{font-size:34px;font-weight:900}}.lab{{font-size:11px;opacity:.6}}
.mxn{{font-size:12px;font-weight:900;margin-top:6px;color:#22c55e;background:rgba(34,197,94,.2);padding:4px 10px;border-radius:12px}}
.bola{{font-size:11px;font-weight:800;text-align:center;margin-top:8px}}.by{{color:#facc15}}.bb{{color:#60a5fa}}</style></head>
<body><div class="wrap">
<div class="side left"><div class="h hy">◆ BINANCE - CRYPTO REAL</div><div class="sub">Total REAL: ${tb:.2f}</div>
<div class="circle cy"><div class="lab">Capital REAL</div><div class="cap">${tb:.2f}</div><div class="mxn">≈ ${tb*usdmxn:,.0f} MXN</div></div>
<div class="bola by">bola ${bb:.2f}<br>D:{s.get('disponible_usd',0):.2f} B:{s.get('bloqueado_usd',0):.2f} G:{s.get('gan_acum',0):.2f}</div></div>
<div class="side right"><div class="h hb">📊 MT5 SIN MT5 REAL</div><div class="sub">Total REAL: ${tm:.2f}</div>
<div class="circle cb"><div class="lab">Capital REAL</div><div class="cap">${tm:.2f}</div><div class="mxn">≈ ${tm*usdmxn:,.0f} MXN</div></div>
<div class="bola bb">bola ${bm:.2f}<br>D:{s.get('disponible_m',0):.2f} B:{s.get('bloqueado_m',0):.2f} G:{s.get('gan_mt5',0):.2f}</div></div>
</div><script>setInterval(()=>location.reload(),15000)</script></body></html>
""")

@app.get("/dashboard")
async def dash():
 r=safe_html("dashboard.html")
 return r if r else await index()

@app.get("/dashboard.html")
async def dash_html():
 r=safe_html("dashboard.html")
 return r if r else await index()

@app.get("/dashboard_mt5.html")
async def dash_mt5():
 r=safe_html("dashboard_mt5.html")
 return r if r else await index()

@app.get("/dual_v5.html")
async def dual():
 return await index()

@app.get("/api/state")
async def state():
 s=load()
 s["total_b"]=float(s.get("disponible_usd",0)+s.get("bloqueado_usd",0)+s.get("gan_acum",0))
 s["total_m"]=float(s.get("disponible_m",0)+s.get("bloqueado_m",0)+s.get("gan_mt5",0))
 s["bola_b"]=s["total_b"]/max(1,s.get("max_entradas",8))
 s["bola_m"]=s["total_m"]/max(1,s.get("max_m",8))
 return s

@app.get("/api/backup")
async def backup():
 return JSONResponse(load())

@app.post("/api/restore")
async def restore(req:Request):
 s=await req.json()
 save(s)
 return {"ok":True}

@app.post("/api/config")
async def config(req:Request):
 s=load()
 d=await req.json()
 for k in ["modo","modo_m","max_entradas","max_m","tp","sl_pct","tp_m","sl_m","auto","auto_m"]:
  if k in d: s[k]=d[k]
 save(s)
 return s

@app.post("/telegram")
async def telegram_webhook(req: Request):
 try:
  data = await req.json()
  msg = data.get("message", {})
  chat_id = msg.get("chat", {}).get("id")
  if chat_id:
   s=load()
   s["last_chat_id"]=chat_id
   save(s)
  return {"ok": True}
 except:
  return {"ok": True}
