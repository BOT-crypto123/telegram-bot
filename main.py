from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os, time
from datetime import datetime

app = FastAPI()
DEFAULT = {
 "disponible_usd":500,"bloqueado_usd":0,"gan_acum":0,
 "disponible_m":500,"bloqueado_m":0,"gan_mt5":0,
 "max_entradas":8,"max_m":8,"tp":0.3,"sl_pct":2.5,"tp_m":0.3,"sl_m":2.5,
 "auto":True,"auto_m":True,"modo":"AMBOS","modo_m":"AMBOS",
 "rsi_compra":40,"rsi_venta":70,"rsi_compra_m":40,"rsi_venta_m":70,
 "coins_activas":{"ADA":True,"AVAX":True,"BNB":True,"BTC":True,"DOGE":True,"ETH":True,"SOL":True,"XRP":True},
 "coins_mt5_activas":{"XAUUSD":True,"XAGUSD":True,"USOIL":True,"SPX500":True,"EURUSD":True,"GBPUSD":True,"NAS100":True,"GER40":True},
 "pos":[],"pos_m":[],"pos_m_short":[],"historial":[],"historial_m":[],"evolucion":[],"evolucion_m":[]
}
def load():
 try:
  with open("state.json","r") as f: s=json.load(f)
  for k,v in DEFAULT.items():
   if k not in s: s[k]=v
  if not s.get("coins_activas"): s["coins_activas"]=DEFAULT["coins_activas"]
  if not s.get("coins_mt5_activas"): s["coins_mt5_activas"]=DEFAULT["coins_mt5_activas"]
  s["max_entradas"]=8; s["max_m"]=8
  if s["disponible_usd"]>500: s["disponible_usd"]=500
  if s["disponible_m"]>500: s["disponible_m"]=500
  return s
 except: return DEFAULT.copy()
def save(s):
 with open("state.json","w") as f: json.dump(s,f)

@app.get("/")
async def index():
 with open("index.html","r") as f: return HTMLResponse(f.read())
@app.get("/dashboard")
async def dash():
 with open("dashboard.html","r") as f: return HTMLResponse(f.read())
@app.get("/dashboard_mt5.html")
async def dash_mt5():
 with open("dashboard_mt5.html","r") as f: return HTMLResponse(f.read())

@app.get("/api/state")
async def state(): return load()

@app.post("/api/config")
async def config(req:Request):
 s=load(); d=await req.json()
 if "toggle_coin" in d: s["coins_activas"][d["toggle_coin"]] = not s["coins_activas"].get(d["toggle_coin"],False)
 if "toggle_coin_mt5" in d: s["coins_mt5_activas"][d["toggle_coin_mt5"]] = not s["coins_mt5_activas"].get(d["toggle_coin_mt5"],False)
 if "max_entradas" in d: s["max_entradas"]=int(d["max_entradas"])
 if "max_m" in d: s["max_m"]=int(d["max_m"])
 for k in ["tp","sl_pct","tp_m","sl_m","modo","modo_m","rsi_compra","rsi_venta","rsi_compra_m","rsi_venta_m","auto","auto_m"]:
  if k in d: s[k]=d[k]
 save(s); return s

@app.post("/api/toggle")
async def toggle(req:Request):
 s=load(); d=await req.json()
 if d.get("side")=="bin": s["auto"]=not s["auto"]
 if d.get("side")=="mt5": s["auto_m"]=not s["auto_m"]
 save(s); return s

@app.post("/api/buy/{sym}")
async def buy(sym:str, req:Request):
 s=load(); data=await req.json() if req else {}
 bola = ((s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"])/8) if s["disponible_usd"]>0 else 62.5
 if s["disponible_usd"]>=bola:
  s["disponible_usd"]-=bola; s["bloqueado_usd"]+=bola
  s["pos"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":data.get("tipo","LONG"),"fecha":datetime.now().isoformat()})
  save(s)
 return s

@app.post("/api/buy_mt5/{sym}")
async def buy_mt5(sym:str, req:Request):
 s=load(); data=await req.json() if req else {}
 bola = ((s["disponible_m"]+s["bloqueado_m"]+s["gan_mt5"])/8) if s["disponible_m"]>0 else 62.5
 if s["disponible_m"]>=bola:
  s["disponible_m"]-=bola; s["bloqueado_m"]+=bola
  s["pos_m"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":data.get("tipo","LONG"),"fecha":datetime.now().isoformat()})
  save(s)
 return s

@app.post("/api/sell/{sym}")
async def sell(sym:str):
 s=load()
 for p in s["pos"]:
  if p["sym"]==sym:
   gan = p["size"]*0.003
   s["bloqueado_usd"]-=p["size"]; s["disponible_usd"]+=p["size"]+gan; s["gan_acum"]+=gan
   s["historial"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":gan,"gan_mxn":gan*16.96,"cap":s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"]})
   s["pos"]=[x for x in s["pos"] if x["sym"]!=sym]; break
 save(s); return s

@app.post("/api/sell_mt5/{sym}")
async def sell_mt5(sym:str):
 s=load()
 for p in s["pos_m"]+s["pos_m_short"]:
  if p["sym"]==sym:
   gan = p["size"]*0.003
   s["bloqueado_m"]-=p["size"]; s["disponible_m"]+=p["size"]+gan; s["gan_mt5"]+=gan
   s["historial_m"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":gan})
   s["pos_m"]=[x for x in s["pos_m"] if x["sym"]!=sym]; s["pos_m_short"]=[x for x in s["pos_m_short"] if x["sym"]!=sym]; break
 save(s); return s

@app.get("/api/backup")
async def backup(): return JSONResponse(load())
@app.post("/api/restore")
async def restore(req:Request):
 s=await req.json(); save(s); return {"ok":True}
