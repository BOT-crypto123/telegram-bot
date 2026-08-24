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
  if not s.get("coins_activas"): s["coins_activas"]=DEFAULT["coins_activas"]
  if not s.get("coins_mt5_activas"): s["coins_mt5_activas"]=DEFAULT["coins_mt5_activas"]
  return s
 except:
  return DEFAULT.copy()

def save(s):
 with open("state.json","w") as f: json.dump(s,f)

def tg_send(text):
 s=load()
 chat_id=s.get("last_chat_id")
 if not BOT_TOKEN or not chat_id: return
 try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=5)
 except: pass

# --- CAMBIO DUAL V5 - PORTADA PRINCIPAL ---
@app.get("/")
async def index():
 try:
  with open("dual_v5.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())
 except:
  with open("index.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.get("/dual_v5.html")
async def dual_v5_page():
 with open("dual_v5.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.get("/dashboard")
async def dash():
 with open("dashboard.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.get("/dashboard_mt5.html")
async def dash_mt5():
 with open("dashboard_mt5.html","r", encoding="utf-8") as f: return HTMLResponse(f.read())
# --- FIN CAMBIO ---

@app.get("/api/state")
async def state(): return load()

@app.post("/api/config")
async def config(req:Request):
 s=load(); d=await req.json()
 if "toggle_coin" in d: s["coins_activas"][d["toggle_coin"]] = not s["coins_activas"].get(d["toggle_coin"],False)
 if "toggle_coin_mt5" in d: s["coins_mt5_activas"][d["toggle_coin_mt5"]] = not s["coins_mt5_activas"].get(d["toggle_coin_mt5"],False)
 if "modo" in d: s["modo"]=d["modo"]
 if "bolas" in d:
  total=int(d["bolas"]); s["max_entradas"]=total
  if s["modo"]=="AMBOS": s["bolas_long"]=total//2; s["bolas_short"]=total//2
  elif s["modo"]=="LONG": s["bolas_long"]=total; s["bolas_short"]=0
  else: s["bolas_long"]=0; s["bolas_short"]=total
 if "cierre" in d: s["cierre"]=float(d["cierre"]); s["tp"]=float(d["cierre"])
 if "tp" in d: s["tp"]=float(d["tp"]); s["cierre"]=float(d["tp"])
 if "sl" in d: s["sl_pct"]=abs(float(d["sl"]))
 if "sl_pct" in d: s["sl_pct"]=abs(float(d["sl_pct"]))
 if "rsi_venta" in d: s["rsi_venta"]=int(d["rsi_venta"])
 if "rsi_compra" in d: s["rsi_compra"]=int(d["rsi_compra"])
 if "rsi_venta_m" in d: s["rsi_venta_m"]=int(d["rsi_venta_m"])
 if "rsi_compra_m" in d: s["rsi_compra_m"]=int(d["rsi_compra_m"])
 if "modo_m" in d: s["modo_m"]=d["modo_m"]
 if "bolas_m" in d:
  total=int(d["bolas_m"]); s["max_m"]=total
  if s.get("modo_m")=="AMBOS": s["bolas_long_m"]=total//2; s["bolas_short_m"]=total//2
  elif s.get("modo_m")=="LONG": s["bolas_long_m"]=total; s["bolas_short_m"]=0
  else: s["bolas_long_m"]=0; s["bolas_short_m"]=total
 if "cierre_m" in d: s["cierre_m"]=float(d["cierre_m"]); s["tp_m"]=float(d["cierre_m"])
 if "tp_m" in d: s["tp_m"]=float(d["tp_m"]); s["cierre_m"]=float(d["tp_m"])
 if "sl_m" in d: s["sl_m"]=abs(float(d["sl_m"]))
 if "rsi_v_m" in d: s["rsi_venta_m"]=int(d["rsi_v_m"])
 if "rsi_c_m" in d: s["rsi_compra_m"]=int(d["rsi_c_m"])
 if "ema" in d: s["ema"]=d["ema"]
 if "ema_m" in d: s["ema_m"]=d["ema_m"]
 if "auto_tune" in d: s["auto"]=bool(d["auto_tune"])
 if "auto" in d: s["auto"]=bool(d["auto"])
 if "auto_m" in d: s["auto_m"]=bool(d["auto_m"])
 if "auto_tune_m" in d: s["auto_m"]=bool(d["auto_tune_m"])
 for k in ["max_entradas","max_m","tp","sl_pct","tp_m","sl_m","modo","modo_m","rsi_compra","rsi_venta","rsi_compra_m","rsi_venta_m"]:
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
 s=load(); data={}
 try: data=await req.json()
 except: pass
 if not s.get("auto",True):
  tg_send(f"🔔 ALERTA ENTRADA BINANCE OFF: {sym} {data.get('tipo','LONG')} RSI {data.get('rsi','?')} Precio {data.get('price',0)} - AUTO OFF no compro, solo aviso")
  return {"ok":True,"alerta":"AUTO OFF BINANCE"}
 total = s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"]
 bola = total / s.get("max_entradas",8) if total>0 else 62.5
 if s["disponible_usd"]>=bola:
  s["disponible_usd"]-=bola; s["bloqueado_usd"]+=bola
  s["pos"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":data.get("tipo","LONG"),"fecha":datetime.now().isoformat()})
  save(s)
  tg_send(f"🤖 AUTO ON BINANCE COMPRÓ: {sym} {data.get('tipo','LONG')} ${bola:.2f} Entry {data.get('price',0)}")
 return s

@app.post("/api/buy_mt5/{sym}")
async def buy_mt5(sym:str, req:Request):
 s=load(); data={}
 try: data=await req.json()
 except: pass
 if not s.get("auto_m",True):
  tg_send(f"🔔 ALERTA ENTRADA MT5 OFF: {sym} {data.get('tipo','LONG')} RSI {data.get('rsi','?')} Precio {data.get('price',0)} - AUTO OFF MT5 no compro, solo aviso")
  return {"ok":True,"alerta":"AUTO OFF MT5"}
 total = s["disponible_m"]+s["bloqueado_m"]+s["gan_mt5"]
 bola = total / s.get("max_m",8) if total>0 else 62.5
 if s["disponible_m"]>=bola:
  s["disponible_m"]-=bola; s["bloqueado_m"]+=bola
  tipo = data.get("tipo","LONG")
  if tipo=="SHORT": s["pos_m_short"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":tipo,"fecha":datetime.now().isoformat()})
  else: s["pos_m"].append({"sym":sym,"size":bola,"entry":data.get("price",0),"tipo":tipo,"fecha":datetime.now().isoformat()})
  save(s)
  tg_send(f"🤖 AUTO ON MT5 COMPRÓ: {sym} {tipo} ${bola:.2f} Entry {data.get('price',0)}")
 return s

@app.post("/api/sell/{sym}")
async def sell(sym:str, req:Request=None):
 s=load()
 data={}
 try:
  if req: data=await req.json()
 except: pass
 if not s.get("auto",True):
  tg_send(f"🔔 ALERTA SALIDA BINANCE OFF: {sym} - Gan estimada {data.get('gan',0)} - AUTO OFF no vendo, solo aviso")
  return {"ok":True,"alerta":"AUTO OFF BINANCE"}
 for p in s["pos"]:
  if p["sym"]==sym:
   gan = p["size"]*(s.get("tp",0.3)/100)
   s["bloqueado_usd"]-=p["size"]; s["disponible_usd"]+=p["size"]+gan; s["gan_acum"]+=gan
   s["historial"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":round(gan,4),"gan_mxn":round(gan*16.96,2),"cap":round(s["disponible_usd"]+s["bloqueado_usd"]+s["gan_acum"],2)})
   s["pos"]=[x for x in s["pos"] if x["sym"]!=sym]; break
 save(s)
 tg_send(f"💰 AUTO ON BINANCE VENDIÓ: {sym} Gan ${gan:.4f}")
 return s

@app.post("/api/sell_mt5/{sym}")
async def sell_mt5(sym:str, req:Request=None):
 s=load()
 data={}
 try:
  if req: data=await req.json()
 except: pass
 if not s.get("auto_m",True):
  tg_send(f"🔔 ALERTA SALIDA MT5 OFF: {sym} - AUTO OFF no vendo, solo aviso")
  return {"ok":True,"alerta":"AUTO OFF MT5"}
 for p in s["pos_m"]+s["pos_m_short"]:
  if p["sym"]==sym:
   gan = p["size"]*(s.get("tp_m",0.5)/100)
   s["bloqueado_m"]-=p["size"]; s["disponible_m"]+=p["size"]+gan; s["gan_mt5"]+=gan
   s["historial_m"].append({"fecha":datetime.now().isoformat(),"moneda":sym,"gan":round(gan,4)})
   s["pos_m"]=[x for x in s["pos_m"] if x["sym"]!=sym]; s["pos_m_short"]=[x for x in s["pos_m_short"] if x["sym"]!=sym]; break
 save(s)
 tg_send(f"💰 AUTO ON MT5 VENDIÓ: {sym} Gan ${gan:.4f}")
 return s

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
  text = (msg.get("text") or "").strip().upper()
  chat_id = msg.get("chat", {}).get("id")
  if not chat_id: return {"ok": True}
  s=load(); s["last_chat_id"]=chat_id; save(s)
  if "DASHBOARD" in text:
   reply = f"""DUAL V5 AMBAS $1000 - PORTADA

🔥 DUAL V5 PORTADA:
{RENDER_URL}/dual_v5.html

DASHBOARD BINANCE $500:
{RENDER_URL}/dashboard
MODO {s.get('modo')} {s.get('max_entradas')} bolas SL {s.get('sl_pct')}% RSI {s.get('rsi_compra')}/{s.get('rsi_venta')} AUTO {'ON 🤖' if s.get('auto') else 'OFF 🔕'}

MT5 Detalle $500:
{RENDER_URL}/dashboard_mt5.html
MODO {s.get('modo_m')} {s.get('max_m')} bolas SL {s.get('sl_m')}% RSI {s.get('rsi_compra_m')}/{s.get('rsi_venta_m')} AUTO {'ON 🤖' if s.get('auto_m') else 'OFF 🔕'}"""
  else:
   reply = "Comandos: DASHBOARD"
  if BOT_TOKEN:
   requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply}, timeout=5)
  return {"ok": True}
 except Exception as e:
  print("telegram error:", e)
  return {"ok": True}
