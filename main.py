from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json, os, requests
from datetime import datetime

app = FastAPI()
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://telegram-bot-cijp.onrender.com"

DEFAULT = {
 "disponible_usd":500,"bloqueado_usd":0,"gan_acum":0,
 "disponible_m":500,"bloqueado_m":0,"gan_mt5":0,
 "max_entradas":8,"max_m":8,
 "bolas_long":4,"bolas_short":4,"bolas_long_m":4,"bolas_short_m":4,
 "tp":0.3,"sl_pct":2.5,"tp_m":0.5,"sl_m":3.0,
 "auto":True,"auto_m":True,
 "modo":"AMBOS","modo_m":"AMBOS",
 "rsi_compra":40,"rsi_venta":70,"rsi_compra_m":50,"rsi_venta_m":65,
 "ema":"OFF Caida","ema_m":"EMA200 ORO",
 "cierre":0.1,"cierre_m":0.5,
 "last_chat_id": None,
 "coins_activas":{"ADA":True,"AVAX":True,"BNB":True,"BTC":True,"DOGE":True,"ETH":True,"SOL":True,"XRP":True},
 "coins_mt5_activas":{"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True,"EURUSD":True,"GBPUSD":True,"NAS100":True,"GER40":True},
 "pos":[],"pos_m":[],"pos_m_short":[],"historial":[],"historial_m":[],"evolucion":[],"evolucion_m":[]
}

def load():
 try:
  with open("state.json","r") as f: s=json.load(f)
  for k,v in DEFAULT.items():
   if k not in s: s[k]=v
  return s
 except:
  return DEFAULT.copy()

def save(s):
 with open("state.json","w") as f: json.dump(s,f)

def safe_html(filename):
    try:
        if os.path.exists(filename):
            with open(filename,"r", encoding="utf-8") as f: return HTMLResponse(f.read())
    except: pass
    with open("index.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.get("/")
async def index(): return safe_html("index.html")
@app.get("/dual_v5.html")
async def dual_v5_page(): return safe_html("index.html")
@app.get("/dashboard")
async def dash(): return safe_html("dashboard.html")
@app.get("/dashboard.html")
async def dash_html(): return safe_html("dashboard.html")
@app.get("/dashboard_mt5.html")
async def dash_mt5(): return safe_html("dashboard_mt5.html")

@app.get("/api/state")
async def state():
    s = load()
    # TOTAL REAL VIVO - FIX DEFINITIVO
    s["total_b"] = float(s.get("disponible_usd",0) + s.get("bloqueado_usd",0) + s.get("gan_acum",0))
    s["total_m"] = float(s.get("disponible_m",0) + s.get("bloqueado_m",0) + s.get("gan_mt5",0))
    if s["total_b"] < 1: s["total_b"] = 500
    if s["total_m"] < 1: s["total_m"] = 500
    s["bola_b"] = s["total_b"] / max(1,s.get("max_entradas",8))
    s["bola_m"] = s["total_m"] / max(1,s.get("max_m",8))
    return s

@app.post("/api/config")
async def config(req:Request):
 s=load(); d=await req.json()
 if "toggle_coin" in d: s["coins_activas"][d["toggle_coin"]] = not s["coins_activas"].get(d["toggle_coin"],False)
 if "toggle_coin_mt5" in d: s["coins_mt5_activas"][d["toggle_coin_mt5"]] = not s["coins_mt5_activas"].get(d["toggle_coin_mt5"],False)
 for k in ["modo","modo_m","max_entradas","max_m","tp","sl_pct","tp_m","sl_m","rsi_compra","rsi_venta","rsi_compra_m","rsi_venta_m","cierre","cierre_m","ema","ema_m","auto","auto_m"]:
  if k in d: s[k]=d[k]
 if "bolas" in d:
  total=int(d["bolas"]); s["max_entradas"]=total
  if s["modo"]=="AMBOS": s["bolas_long"]=total//2; s["bolas_short"]=total//2
  elif s["modo"]=="LONG": s["bolas_long"]=total; s["bolas_short"]=0
  else: s["bolas_long"]=0; s["bolas_short"]=total
 if "bolas_m" in d:
  total=int(d["bolas_m"]); s["max_m"]=total
  if s.get("modo_m")=="AMBOS": s["bolas_long_m"]=total//2; s["bolas_short_m"]=total//2
  elif s.get("modo_m")=="LONG": s["bolas_long_m"]=total; s["bolas_short_m"]=0
  else: s["bolas_long_m"]=0; s["bolas_short_m"]=total
 save(s); return s

@app.post("/api/toggle")
async def toggle(req:Request):
 s=load(); d=await req.json()
 if d.get("side")=="bin": s["auto"]=not s["auto"]
 if d.get("side")=="mt5": s["auto_m"]=not s["auto_m"]
 save(s); return s

@app.post("/api/buy/{sym}")
async def buy(sym:str, req:Request):
 s=load(); data={}
 try: data=await req.json()
 except: pass
 if not s.get("auto",True): return {"ok":True}
 total = s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"]
 bola = total / s.get("max_entradas",8) if total>0 else 62.5
 if s["disponible_usd"]>=bola:
  s["disponible_usd"]-=bola; s["bloqueado_usd"]+=bola
  s["pos"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":data.get("tipo","LONG"),"fecha":datetime.now().isoformat()})
  save(s)
 return s

@app.post("/api/buy_mt5/{sym}")
async def buy_mt5(sym:str, req:Request):
 s=load(); data={}
 try: data=await req.json()
 except: pass
 if not s.get("auto_m",True): return {"ok":True}
 total = s["disponible_m"]+s["bloqueado_m"]+s["gan_mt5"]
 bola = total / s.get("max_m",8) if total>0 else 62.5
 if s["disponible_m"]>=bola:
  s["disponible_m"]-=bola; s["bloqueado_m"]+=bola
  tipo = data.get("tipo","LONG")
  if tipo=="SHORT": s["pos_m_short"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":tipo,"fecha":datetime.now().isoformat()})
  else: s["pos_m"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":tipo,"fecha":datetime.now().isoformat()})
  save(s)
 return s

@app.post("/api/sell/{sym}")
async def sell(sym:str, req:Request=None):
 s=load()
 for p in s["pos"]:
  if p["sym"]==sym:
   gan = p["size"]*(s.get("tp",0.3)/100)
   s["bloqueado_usd"]-=p["size"]; s["disponible_usd"]+=p["size"]+gan; s["gan_acum"]+=gan
   s["historial"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":round(gan,4)})
   s["pos"]=[x for x in s["pos"] if x["sym"]!=sym]; break
 save(s); return s

@app.post("/api/sell_mt5/{sym}")
async def sell_mt5(sym:str, req:Request=None):
 s=load()
 for p in s["pos_m"]+s["pos_m_short"]:
  if p["sym"]==sym:
   gan = p["size"]*(s.get("tp_m",0.5)/100)
   s["bloqueado_m"]-=p["size"]; s["disponible_m"]+=p["size"]+gan; s["gan_mt5"]+=gan
   s["historial_m"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":round(gan,4)})
   s["pos_m"]=[x for x in s["pos_m"] if x["sym"]!=sym]; s["pos_m_short"]=[x for x in s["pos_m_short"] if x["sym"]!=sym]; break
 save(s); return s

@app.get("/api/backup")
async def backup(): return JSONResponse(load())
@app.post("/api/restore")
async def restore(req:Request):
 s=await req.json(); save(s); return {"ok":True}

@app.post("/telegram")
async def telegram_webhook(req: Request):
 try:
  data = await req.json()
  msg = data.get("message", {})
  chat_id = msg.get("chat", {}).get("id")
  if not chat_id: return {"ok": True}
  s=load(); s["last_chat_id"]=chat_id; save(s)
  if BOT_TOKEN:
   import requests as rq
   rq.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"{RENDER_URL}/"}, timeout=5)
  return {"ok": True}
 except: return {"ok": True}
